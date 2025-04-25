# Ankidecker

Ankidecker is a tool that allows you to create Anki decks from a list of terms/words. The backsides/definitions/answers of the cards can be generated automatically using an implementation of the `DefinitionFetcher` interface. Currently, the only implementation (besides a Dummy one) is `DeepInfraFetcher`, which uses the DeepInfra API to fetch definitions.

The `DeepInfraFetcher` is a wrapper around the DeepInfra API, which is a paid service. You can use the `DummyFetcher` to test the functionality of Ankidecker without needing an API key. You can also implement your own `DefinitionFetcher` if you want to use a different service to fetch definitions (e.g. Wikipedia, Google, Translate, etc.). The `DefinitionFetcher` interface is very simple:

```python
class DefinitionFetcher(ABC):
    @abstractmethod
    def fetch(self, term: str) -> tuple[str, bool]:
        """Fetches the definition for a given term. The flag indicates if the term was found in the cache."""
        pass

    @abstractmethod
    def close(self):
        """Closes any resources used by the fetcher (you can do things such as saving the cache here)."""
        pass
```

The `fetch` method takes a term as input and returns a tuple containing the definition and a boolean flag indicating if the term was found in the cache. The `close` method is used to close any resources used by the fetcher (e.g. database connections, file handles, etc.), or to do things such as saving the cache. You can look at the `DeepInfraFetcher` and `DummyFetcher` classes for examples of how to implement the `DefinitionFetcher` interface.

## Usage

```sh
$ python ankidecker.py --help

usage: ankidecker.py [-h] -i INPUT_PATH -o OUTPUT_PATH [-m {debug,anki}] [-f {dummy,deepinfra}]

Fetch definitions for terms and save them in a specified format.

options:
  -h, --help            show this help message and exit
  -i INPUT_PATH, --input_path INPUT_PATH
                        Path to the input file containing terms. Each term should be on a new line.
  -o OUTPUT_PATH, --output_path OUTPUT_PATH
                        Path to the output file where definitions will be saved.
  -m {debug,anki}, --out_mode {debug,anki}
                        Output mode: 'debug' for plain text, 'anki' for Anki deck. Tries to guess the mode from the output file extension if not specified.    
  -f {dummy,deepinfra}, --fetcher {dummy,deepinfra}
                        Fetcher to use: 'dummy' for testing, 'deepinfra' for real API calls (requires environment variable DEEPINFRA_API_KEY). Default is      
                        'deepinfra'.

# Example usage:

$ cd my_project_directory

$ cat terms.txt
Some niche term 1
Some niche term 2
Some niche term 3
Some niche term 4

# create a human readable debug text file with dummy definitions
$ python /path/to/ankidecker.py -i terms.txt -o definitions.txt -m debug -f dummy

# set environment variable DEEPINFRA_API_KEY to your DeepInfra API key
$ export DEEPINFRA_API_KEY=your_api_key

# create an Anki deck with real definitions using DeepInfra API
# the output file will be an Anki deck file (.apkg)
$ python /path/to/ankidecker.py -i terms.txt -o terms_anki_deck.apkg -m anki -f deepinfra
```

You can change the system/user prompt in the `ankidecker.py` file.

> When I have time (if this gets any interest / stars) I will provide a way to configure the prompt (and generally use the package) without going into the source code.
> I will also add a way to use the package as a library (currently it is only usable as a command line tool).
> The interface could also be improved to allow asynchronous (parallel) fetches especially for large lists of terms.
> 
> The output format is not hardcoded to Anki, you can also implement your own output format by implementing the `OutputStrategy` interface:

```python
class OutputStrategy(ABC):
    @abstractmethod
    def output(self, terms_with_defs: list, output_path: str):
        """
        Saves the terms and definitions to the specified output path using the implemented strategy.
        :param terms_with_defs: List of tuples containing terms and their definitions.
        :param output_path: Path to the output file.
        """
        pass
```

> So you can implement your own output format (e.g. CSV, JSON, etc.) if you want to use a different format than Anki. You can look at the `AnkiOutputStrategy` or the barebones `DebugOutputStrategy` class for an example of how to implement the `OutputStrategy` interface.

---

The resulting `.apkg` file can be imported into Anki using any of the Anki clients (desktop, Android, iOS). The front side of the cards will contain the terms, and the back side will contain the definitions fetched from the API.
