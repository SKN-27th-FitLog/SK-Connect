import os

replacements = {
    'from src.core.storage': 'from src.core.storage',
    'import src.core.storage': 'import src.core.storage',
    'from src.core.utils': 'from src.core.utils',
    'import src.core.utils': 'import src.core.utils',
    'from src.db.repositories': 'from src.db.repositories',
    'from src.db.models': 'from src.db.models',
    'from src.db.queries': 'from src.db.queries',
    'from src.services.parsers': 'from src.services.parsers',
    'from src.services.collectors': 'from src.services.collectors',
    'from src.services.validators': 'from src.services.validators',
}

def update_file(filepath):
    # Skip .venv
    if '.venv' in filepath:
        return

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # If it's not UTF-8, try other encodings or just skip
        print(f"Skipping {filepath} due to decoding error.")
        return
    
    new_content = content
    for old, new in replacements.items():
        new_content = new_content.replace(old, new)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
            print(f"Updated absolute imports in {filepath}")

# 1. Update Absolute src. imports everywhere
for root, dirs, files in os.walk('.'):
    if '.venv' in dirs:
        dirs.remove('.venv')
    for file in files:
        if file.endswith('.py'):
            update_file(os.path.join(root, file))

# 2. Update relative imports in specific folders (One level down move)
# For files in src/db/models, queries, repositories
# For files in src/services/collectors, parsers, validators
# We need to change ..core to ...core, ..utils to ...core.utils

level_shift_folders = [
    'src/db/models', 'src/db/queries', 'src/db/repositories',
    'src/services/collectors', 'src/services/parsers', 'src/services/validators'
]

relative_replacements = {
    'from ..core': 'from ...core',
    'from ..utils': 'from ...core.utils',
}

for folder in level_shift_folders:
    if not os.path.exists(folder):
        continue
    for file in os.listdir(folder):
        if file.endswith('.py'):
            filepath = os.path.join(folder, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content
            # CAUTION: from ..db_client -> from ...core.db_client? No.
            # Only if the original imported from the sibling of old location.
            # Old repositories/ sibling was core. So ..core worked.
            # Now db/repositories/ sibling is db/queries. core is at ...core.
            for old, new in relative_replacements.items():
                new_content = new_content.replace(old, new)
            
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                    print(f"Updated relative imports in {filepath}")

# 3. Update relative imports in src/pipeline and src/handlers
# These didn't move, but siblings moved.
# from ..models -> from ..db.models
# from ..repositories -> from ..db.repositories
# from ..collectors -> from ..services.collectors
# from ..parsers -> from ..services.parsers
# from ..validators -> from ..services.validators
# from ..utils -> from ..core.utils (moved under core)
# from ..storage -> from ..core.storage (moved under core)

pipeline_handlers_folders = ['src/pipeline', 'src/handlers']
sibling_replacements = {
    'from ..repositories': 'from ..db.repositories',
    'from ..models': 'from ..db.models',
    'from ..queries': 'from ..db.queries',
    'from ..collectors': 'from ..services.collectors',
    'from ..parsers': 'from ..services.parsers',
    'from ..validators': 'from ..services.validators',
    'from ..utils': 'from ..core.utils',
    'from ..storage': 'from ..core.storage',
}

for folder in pipeline_handlers_folders:
    if not os.path.exists(folder):
        continue
    for file in os.listdir(folder):
        if file.endswith('.py'):
            filepath = os.path.join(folder, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content
            for old, new in sibling_replacements.items():
                new_content = new_content.replace(old, new)
            
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                    print(f"Updated sibling relative imports in {filepath}")
