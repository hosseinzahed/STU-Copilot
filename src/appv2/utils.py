import os
from dotenv import load_dotenv, dotenv_values

load_dotenv(override=True)

def check_env_vars() -> None:
    """Check if the required environment variables are set.

    Args:
        required_vars (list[str]): List of required environment variable names. 
    Raises:
        EnvironmentError: If any required environment variable is not set.
    """
    
    # Get all variables defined in the .env file
    required_vars = list(dotenv_values('.env').keys())
        
    # Check for missing environment variables
    missing = [var for var in required_vars if not os.getenv(var)]
    
    # Raise an error
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")
    
if __name__ == "__main__":
    check_env_vars()