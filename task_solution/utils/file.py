def load_file(file_path: str) -> str:
    """
    Load a file and return its content as a string.
    
    :param file_path: Path to the file to be loaded.
    :return: Content of the file as a string.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return content

def save_file(file_path: str, content: str) -> None:
    """
    Save content to a file.
    
    :param file_path: Path to the file where content will be saved.
    :param content: Content to be saved in the file.
    """
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)
        
def append_to_file(file_path: str, content: str) -> None:
    """
    Append content to a file.
    
    :param file_path: Path to the file where content will be appended.
    :param content: Content to be appended to the file.
    """
    with open(file_path, 'a', encoding='utf-8') as file:
        file.write(f"{content}\n")