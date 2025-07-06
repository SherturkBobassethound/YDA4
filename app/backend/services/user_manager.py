# %%
import hashlib

# %%
class UserIdentifier:
    """
    A simple utility class for generating a unique user ID and a corresponding
    collection name from a given username. It uses SHA-256 to create a deterministic
    hash so that the same username always yields the same ID.

    This class is kept simple and independent of authentication or DB logic.
    """
    
    @staticmethod
    def generate_user_id(username: str) -> str:
        """
        Generate a unique, deterministic user ID from a username using SHA-256.
        
        Args:
            username (str): The username provided by the user.
        
        Returns:
            str: A hexadecimal hash string representing the unique user ID.
        """
        return hashlib.sha256(username.strip().lower().encode()).hexdigest()
    
    @staticmethod
    def get_collection_name(username: str, prefix: str = "user", short: bool = True, length: int = 12) -> str:
        """
        Generate a collection name for a vector database based on the username.
        
        Args:
            username (str): The username.
            prefix (str): A prefix to use for the collection name. Default is "user".
            short (bool): Whether to shorten the hash (default True).
            length (int): Length of the shortened hash. Default is 12 characters.
        
        Returns:
            str: The collection name (e.g., "user_abcdef123456").
        """
        uid = UserIdentifier.generate_user_id(username)
        suffix = uid[:length] if short else uid
        return f"{prefix}_{suffix}"

# %%
# Example usage:
if __name__ == "__main__":
    username = "Dwarkesh"
    user_id = UserIdentifier.generate_user_id(username)
    collection_name = UserIdentifier.get_collection_name(username)
    
    print("User ID:", user_id)
    print("Collection Name:", collection_name)