from abc import ABC, abstractmethod
import requests
import genanki
from dotenv import load_dotenv

class DefinitionFetcher(ABC):
    @abstractmethod
    def fetch(self, term: str) -> str:
        """Fetches the definition for a given term."""
        pass

class DummyFetcher(DefinitionFetcher):
    def fetch(self, term: str) -> str:
        # Dummy implementation for testing
        return f"Dummy definition for term \"{term}\""

class DeepInfraFetcher(DefinitionFetcher):
    def __init__(self, api_key: str, model: str = "deepseek-ai/DeepSeek-V3-0324"):
        self.api_key = api_key
        self.model = model

    def fetch(self, term: str) -> str:
        system_prompt = (
            "You are an expert in startups and business education. Provide concise definitions in Russian for key startup terminology, "
            "suitable for inclusion in educational flashcards. Each definition should be 1–2 sentences and clear to a university-level student."
        )
        user_prompt = f"Дай краткое определение термина «{term}» в контексте стартапов и бизнеса на русском языке."
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        json_data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
        }
        response = requests.post("https://api.deepinfra.com/v1/chat/completions", headers=headers, json=json_data)
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        else:
            print(f"Error fetching definition for {term}: {response.text}")
            return "Ошибка получения определения"

class OutputStrategy(ABC):
    @abstractmethod
    def output(self, terms_with_defs: list, output_path: str):
        pass

class AnkiOutputStrategy(OutputStrategy):
    def output(self, terms_with_defs: list, output_path: str):
        deck_id = 2059400110
        model_id = 1607392319

        my_model = genanki.Model(
            model_id,
            'Startup Terms Model',
            fields=[
                {'name': 'Term'},
                {'name': 'Definition'},
            ],
            templates=[
                {
                    'name': 'Card 1',
                    'qfmt': '{{Term}}',
                    'afmt': '{{FrontSide}}<hr id="answer">{{Definition}}',
                },
            ])

        my_deck = genanki.Deck(
            deck_id,
            'Startup Terms in Russian'
        )

        for term, definition in terms_with_defs:
            note = genanki.Note(
                model=my_model,
                fields=[term, definition]
            )
            my_deck.add_note(note)

        genanki.Package(my_deck).write_to_file(output_path)

class DebugOutputStrategy(OutputStrategy):
    def output(self, terms_with_defs: list, output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            for term, definition in terms_with_defs:
                f.write(f"Term: {term}\nDefinition: {definition}\n\n")

def load_terms(file_path: str) -> list:
    with open(file_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def generate_output(terms: list, fetcher: DefinitionFetcher, output_strategy: OutputStrategy, output_path: str):
    terms_with_defs = [(term, fetcher.fetch(term)) for term in terms]
    output_strategy.output(terms_with_defs, output_path)

if __name__ == "__main__":
    DEBUG_OUTPUT = False
    # Load environment variables from .env file
    load_dotenv()
    
    # input_file = 'terms.txt'
    input_file = 'terms_small.txt'
    output_file = 'startup_terms_debug.txt' if DEBUG_OUTPUT else 'startup_terms_anki.apkg'

    # fetcher = DeepInfraFetcher(api_key=os.getenv("DEEPINFRA_API_KEY"))
    fetcher = DummyFetcher()
    terms = load_terms(input_file)

    # Use either strategy
    strategy = DebugOutputStrategy() if DEBUG_OUTPUT else AnkiOutputStrategy()
    generate_output(terms, fetcher, strategy, output_file)

    print(f"Processed {len(terms)} terms using {strategy.__class__.__name__} and saved to {output_file}.")
