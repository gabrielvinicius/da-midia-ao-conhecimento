import json
import os

def get_all_python_files(directory):
    py_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                py_files.append(os.path.join(root, file).replace('\\', '/'))
    return py_files

def find_unused_modules(pydeps_file, entry_points_paths):
    with open(pydeps_file, 'r', encoding='utf-16') as f:
        # Read the file and fix the JSON
        content = f.read()
        # Remove trailing commas from the last object
        content = content.strip()
        if content.endswith(','):
            content = content[:-1]
        
        # pydeps output is a sequence of JSON objects, need to wrap in a list
        # Also, it seems the output is not a valid JSON array, so we need to add commas between objects
        content = content.replace('}\n{', '},{')
        json_content = f"[{content}]"

    try:
        data_list = json.loads(json_content)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        # Find the position of the error
        error_pos = e.pos
        # Get the 200 characters before and after the error
        context = json_content[max(0, error_pos - 100):error_pos + 100]
        print(f"Context of error:\n...{context}...")
        return

    # Assuming the actual data is the last element in the list
    data = data_list[-1] if data_list else {}

    all_modules = set(data.keys())
    imported_modules = set()

    for module_info in data.values():
        if 'imports' in module_info:
            for imp in module_info['imports']:
                imported_modules.add(imp)
    
    # Convert entry points paths to module names
    entry_points = set()
    for path in entry_points_paths:
        module_name = path.replace('/', '.').replace('.py', '')
        entry_points.add(module_name)

    # We also need to add the main entry points of the application
    entry_points.add('main')
    entry_points.add('src.main')
    entry_points.add('src.celery_app')


    unused_modules = all_modules - imported_modules - entry_points

    # we should also remove the __init__.py files from the unused modules
    unused_modules = {mod for mod in unused_modules if not mod.endswith('.__init__')}


    print("Unused modules:")
    for module in sorted(list(unused_modules)):
        print(module)

if __name__ == '__main__':
    scripts_files = get_all_python_files('scripts')
    tests_files = get_all_python_files('tests')
    entry_points = scripts_files + tests_files
    find_unused_modules('pydeps.json', entry_points)