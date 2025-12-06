"""
text_splitter.py

This module defines the TextSplitter class.

Current functionality:
  - Takes a file path to a text file.
  - Reads the contents of the text file.
  - Splits the text into chunks using LangChain's RecursiveCharacterTextSplitter.
  - Uses sentence-aware separators by default for more coherent, readable chunks.
  - Returns a list of raw string chunks.

Future enhancements:
  - Add support for other file types (e.g., PDF, DOCX) by subclassing or adding new methods.
"""
# %%
from langchain.text_splitter import RecursiveCharacterTextSplitter

class TextSplitter:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, separators: list = None):
        """
        Initialize the TextSplitter with configurable chunk parameters.

        Args:
            chunk_size (int): Maximum number of characters per chunk. Default: 1000.
            chunk_overlap (int): Number of overlapping characters between consecutive chunks. Default: 200 (20% overlap).
            separators (list, optional): Custom separators for splitting text.
                                         If None, uses sentence-aware separators for more coherent chunks.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Use sentence-aware separators by default for more coherent chunks
        if separators is None:
            self.separators = [
                "\n\n",    # Paragraphs (highest priority)
                "\n",      # Lines
                ". ",      # Sentences ending with period
                "? ",      # Sentences ending with question mark
                "! ",      # Sentences ending with exclamation
                "; ",      # Semicolons
                ", ",      # Commas
                " ",       # Words
                ""         # Characters (last resort)
            ]
        else:
            self.separators = separators

        # Initialize the recursive text splitter from LangChain.
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators
        )

    def split_file(self, file_path: str) -> list:
        """
        Reads a text file from the given file path and splits it into chunks.

        Args:
            file_path (str): Path to the text file.

        Returns:
            List[str]: A list of raw string chunks.
        """
        # Load the text from the file.
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        # Split the text into chunks.
        chunks = self.splitter.split_text(text)
        
        # Optionally, filter out any empty chunks.
        return [chunk for chunk in chunks if chunk.strip()]

    def split_text(self, text: str) -> list:
        """
        Splits a raw text string into chunks using the recursive text splitter.

        Args:
            text (str): The raw text to split.

        Returns:
            List[str]: A list of string chunks.
        """
        chunks = self.splitter.split_text(text)
        return [chunk for chunk in chunks if chunk.strip()]


# %%
# Example usage for testing the module:
if __name__ == "__main__":
    # Adjust the file path as needed.
    sample_file_path = "../../../test_data/transcript_dwarkesh-ama-ft-sholto-trenton.txt"
    
    # Create an instance of TextSplitter.
    splitter = TextSplitter(chunk_size=1000, chunk_overlap=200)
    
    # Split the file and retrieve chunks.
    chunks = splitter.split_file(sample_file_path)
    
    print(f"Split the file into {len(chunks)} chunks.")
    for i, chunk in enumerate(chunks):
        print(f"\nCHUNK {i+1}:\n{chunk}")
