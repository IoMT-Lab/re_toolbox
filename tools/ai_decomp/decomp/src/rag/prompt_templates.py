#!/usr/bin/env python3

DEFAULT_TEMPLATE = {
    "header": "# Below are some examples of assembly code and their corresponding C/C++ source code:\n\n",
    "example_start": "## Example {example_num}:\n",
    "assembly_section": "Assembly with {optimization} optimization:\n{assembly_content}\n\n",
    "source_section": "{language} Source Code:\n{source_content}\n\n",
    "query_section": "# This is the assembly code:\n\nAssembly:\n{target_assembly}\n\nWhat is the source code?\n"
}

STATIC_TEMPLATES = {
    "default": DEFAULT_TEMPLATE,
}

AVAILABLE_TEMPLATES = {**STATIC_TEMPLATES}

def get_template(template_name):
    return AVAILABLE_TEMPLATES.get(template_name, DEFAULT_TEMPLATE)