def slug(title):
    """Convert a title to a lowercase URL slug."""
    return title.strip().lower().replace(" ", "-")

