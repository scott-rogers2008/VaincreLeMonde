import subprocess

def get_git_root(path):
    """
    Returns the absolute path of the root of the git repository.
    
    Args:
        path (str): The starting directory to search from.

    Returns:
        str: The absolute path to the repository root.

    Raises:
        IOError: If the current working directory is not a git repository.
    """
    try:
        # Run the git command to get the top-level directory
        base = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=path, stderr=subprocess.DEVNULL)
        # Decode the output from bytes to string and strip whitespace
        return base.decode('utf-8').strip()
    except subprocess.CalledProcessError:
        raise IOError('Current working directory is not a git repository')