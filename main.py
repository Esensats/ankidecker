from abc import ABC, abstractmethod
import os
import json
import time
import requests
import genanki
import markdown2
import argparse
from dotenv import load_dotenv
from tqdm import tqdm


class DefinitionFetcher(ABC):
    @abstractmethod
    def fetch(self, term: str) -> tuple[str, bool]:
        """Fetches the definition for a given term. The flag indicates if the term was found in the cache."""
        pass

    @abstractmethod
    def close(self):
        """Closes any resources used by the fetcher."""
        pass

    @abstractmethod
    def __enter__(self):
        """Enters the context manager."""
        return self

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exits the context manager."""
        self.close()
        return False  # Do not suppress exceptions


class DummyFetcher(DefinitionFetcher):
    def fetch(self, term: str) -> tuple[str, bool]:
        # Dummy implementation for testing
        return f'Dummy definition for term "{term}"', False

    def close(self):
        # No resources to close in dummy fetcher
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class DeepInfraFetcher(DefinitionFetcher):
    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-ai/DeepSeek-V3-0324",
        cache_file: str = "definition_cache.json",
    ):
        if not api_key:
            raise ValueError("API key is required.")
        self.api_key = api_key
        self.model = model
        self.cache_file = cache_file
        self.cache = self._load_cache()
        self._dirty = False  # Track whether cache has been updated
        self._last_save_timestamp = time.time()
        self._save_interval = 15  # Save cache every 15 seconds

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _load_cache(self) -> dict:
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_cache(self):
        if self._dirty:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def fetch(self, term: str) -> tuple[str, bool]:
        if term in self.cache:
            html_def = markdown2.markdown(self.cache[term])
            return html_def, True

        system_prompt = (
            "You are an expert in startups and business education. Provide concise definitions in Russian for key startup terminology, "
            "suitable for direct inclusion in educational flashcards. Each definition should be 1–2 sentences and clear to a university-level student. "
            "No extra explanations, no headings, no intro or outro. You can add an example case (or a usage example) in a "
            "new paragraph if it helps to understand the term. The term itself should be formatted in bold."
        )

        user_prompt = f"Дай краткое определение термина «{term}» в контексте стартапов и бизнеса на русском языке."
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        json_data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        response = requests.post(
            "https://api.deepinfra.com/v1/openai/chat/completions",
            headers=headers,
            json=json_data,
        )
        if response.status_code == 200:
            result = response.json()
            definition = result["choices"][0]["message"]["content"].strip()
            self.cache[term] = definition
            self._dirty = True
            html_def = markdown2.markdown(definition)
            if time.time() - self._last_save_timestamp > self._save_interval:
                self._save_cache()
                self._last_save_timestamp = time.time()
            return html_def, False
        else:
            raise Exception(f"Error fetching definition for {term}: {response.text}")

    def close(self):
        self._save_cache()


class OutputStrategy(ABC):
    @abstractmethod
    def output(self, terms_with_defs: list, output_path: str):
        pass


class TermNote(genanki.Note):
    @property
    def guid(self):
        return genanki.guid_for(self.fields[0])  # type: ignore


class AnkiOutputStrategy(OutputStrategy):
    def output(self, terms_with_defs: list, output_path: str):
        deck_id = 1311755446
        model_id = 1496530154

        my_model = genanki.Model(
            model_id,
            "Startup Terms Model",
            fields=[
                {"name": "Term"},
                {"name": "Definition"},
            ],
            templates=[
                {
                    "name": "Card 1",
                    "qfmt": "{{Term}}",
                    "afmt": '{{FrontSide}}<hr id="answer">{{Definition}}',
                },
            ],
        )

        my_deck = genanki.Deck(deck_id, "Startup Terms in Russian")

        for term, definition in terms_with_defs:
            note = TermNote(model=my_model, fields=[term, definition])
            my_deck.add_note(note)

        genanki.Package(my_deck).write_to_file(output_path)


class DebugOutputStrategy(OutputStrategy):
    def output(self, terms_with_defs: list, output_path: str):
        with open(output_path, "w", encoding="utf-8") as f:
            for term, definition in terms_with_defs:
                f.write(f"Term: {term}\nDefinition: {definition}\n\n")


def load_terms(file_path: str) -> list:
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def generate_output(
    terms: list,
    fetcher: DefinitionFetcher,
    output_strategy: OutputStrategy,
    output_path: str,
):
    terms_with_defs = []
    with tqdm(total=len(terms), desc="Fetching terms", ncols=100) as pbar:
        for term in terms:
            pbar.set_description(f"Fetching: {term}")
            definition, from_cache = fetcher.fetch(term)
            status = "cache" if from_cache else "API"
            pbar.set_description(f"Fetched: {term} ({status})")
            terms_with_defs.append((term, definition))
            pbar.update(1)
    output_strategy.output(terms_with_defs, output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch definitions for terms and save them in a specified format."
    )
    parser.add_argument(
        "-i",
        "--input_path",
        type=str,
        required=True,
        help="Path to the input file containing terms. Each term should be on a new line.",
    )
    parser.add_argument(
        "-o",
        "--output_path",
        type=str,
        required=True,
        help="Path to the output file where definitions will be saved.",
    )
    parser.add_argument(
        "-m",
        "--out_mode",
        type=str,
        choices=["debug", "anki"],
        help="Output mode: 'debug' for plain text, 'anki' for Anki deck. Tries to guess the mode from the output file extension if not specified.",
    )
    parser.add_argument(
        "-f",
        "--fetcher",
        type=str,
        choices=["dummy", "deepinfra"],
        default="deepinfra",
        help="Fetcher to use: 'dummy' for testing, 'deepinfra' for real API calls (requires environment variable DEEPINFRA_API_KEY). Default is 'deepinfra'.",
    )
    
    args = parser.parse_args()

    load_dotenv()

    def get_api_key():
        api_key = os.getenv("DEEPINFRA_API_KEY")
        if not api_key:
            raise ValueError(
                "API key not found. Please set the DEEPINFRA_API_KEY environment variable."
            )
        return api_key

    def get_fetcher():
        if args.fetcher == "dummy":
            return DummyFetcher()
        elif args.fetcher == "deepinfra":
            return DeepInfraFetcher(api_key=get_api_key())
        else:
            raise ValueError(f"Unknown fetcher: {args.fetcher}")

    def get_output_strategy():
        if args.out_mode == "anki" or args.output_path.endswith(".apkg"):
            return AnkiOutputStrategy()
        elif args.out_mode == "debug" or args.output_path.endswith(".txt"):
            return DebugOutputStrategy()
        else:
            raise ValueError(
                "Output mode not specified or unsupported. Use --out_mode 'debug' or 'anki'."
            )

    if not os.path.exists(args.input_path):
        print(f"Input file {args.input_path} does not exist.")
        exit(1)

    with get_fetcher() as fetcher:
        terms = load_terms(args.input_path)
        strategy = get_output_strategy()
        generate_output(terms, fetcher, strategy, args.output_path)
        print(
            f"Processed {len(terms)} terms using {strategy.__class__.__name__} and saved to {args.output_path}."
        )


if __name__ == "__main__":
    main()
