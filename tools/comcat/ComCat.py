# ComCat pipeline for classifying a file. Pass a C/C++ filename as a command line argument and prints the commented file.

import sys
from cparser import get_blocks_str, run_linter
import tempfile
import openai
from config import api_key, model
from utils import remove_markdown_code_block, comment_remover
import argparse


# Initialize the OpenAI API client
openai.api_key = api_key

prompts = [
    """Given the following C/C++ function, generate a Javadoc style comment using this template that summarizes its functionality in 50 words or less. Parts of the template for parameters, return values, and exceptions are optional.

Template:
/**
 * [Function name]
 * @brief [Provide a brief description of the function]
 *
 * [Provide a more detailed explanation of the function's purpose and functionality]
 *
 * @param [param1] [Description of the first parameter]
 * @param [param2] [Description of the second parameter]
 * ...
 * @return [Description of the return value]
 *
 * @exception [ExceptionType] [Description of the exception and when it can occur]
 * ...
 */""",
    """Given the following C/C++ variable, constant, or literal, generate a comment using this template that summarizes its functionality with regards to its use throughout the code in a single line with no line breaks. If there are multiple variables, group them by functionality. If unknown, simply state "unknown" for description and purpose.\n\nTemplate:\n// [Variable/Constant/Literal Name(s)]: [Description and purpose].""",    
    """Given the following C/C++ code, generate a comment using this template that summarizes the code functionality and why it was implemented the way it was in 30 words or less. If it is not relevant, ignore the approach section of the template. \n\nTemplate:\n\n// Function: [Functionality and purpose].\n// Approach: [Approach or strategy].""",
    """Given the following C/C++ code, generate a comment using this template that describes the branch conditions and functionalities in the code in 30 words or less.

Template:
// Cond: [Conditions]
// Function: [Functionality and Purpose]""",
    """Given the following C/C++ code, generate a comment using this template that summarizes the code functionality and why it was implemented the way it was in 30 words or less. If it is not relevant, ignore the approach section of the template. \n\nTemplate:\n\n// Function: [Brief summary of what the code does and its purpose].\n// Approach: [The main approach or strategy used in the code]."""
]





def main():
  # Set up argument parser
  parser = argparse.ArgumentParser(
    description="Process a C file and remove comments, optionally including a second file."
  )
  parser.add_argument(
    "filename",
    type=str,
    help="The path to the C file to comment."
  )
  parser.add_argument(
    "--keep",
    action="store_true",
    help=(
      "Do not remove comments before commenting the file if true. "
      "If false, still preserves comments marked as important (those starting with '!')."
    )
  )
  parser.add_argument(
    "--decomp-file",
    type=str,
    default=None,
    help=(
      "Path to an additional file whose contents will be passed to "
      "`comment_file` as the `decomp` argument."
    )
  )

  args = parser.parse_args()

  # Read the decomp-file if provided
  decomp_str = ""
  if args.decomp_file:
    try:
      with open(args.decomp_file, "r", encoding="utf-8") as f:
        decomp_str = f.read()
    except OSError as e:
      parser.error(f"Could not read decomp file {args.decomp_file!r}: {e}")

  # Generate the commented output
  result = comment_file(
    args.filename,
    decomp=decomp_str,
    remove_comments=not args.keep
  )

  # Write result to a temp file, print its path
  with tempfile.NamedTemporaryFile(
    mode="w",     # write text
    delete=False,   # keep the file
    encoding="utf-8"
  ) as tmp:
    tmp.write(result)
    tmp_path = tmp.name

  #print output filename
  print(tmp_path)

# Comment the file found at the given filepath
def comment_file(filepath, decomp = "", remove_comments=True):

  code = ""
  with open(filepath, 'r') as file:
    code = file.read()

  if remove_comments:
    code = comment_remover(code)

  messages = [
    {"role": "system", "content" : f"You're a C/C++ comment generator. You will generate a "\
        "software comment in 50 words or less that summarizes the C/C++ code you are given. "\
        "This C/C++ source code was decompiled from a software binary for reverse engineering. "\
        "This code was enhanced to be more readable from the following decompiler output: \n{decomp}\n\n"\
        "The code that you will be given will be from the following file: \n{code}"}
  ]

  # blocks gets a list of tuples of (suggested_class, code_block) where the suggested_class is based purely on the C/C++ construct
  blocks = get_blocks_str(code)

  generated_comments = [] #[f"//comment{i}" for i in range(len(blocks))]

  
  # For each code block, find the appropriate comment type to describe it and then generate a comment for that block.
  for tup in blocks:
    pred = tup[0]
    content = prompts[pred] + "\n\nCode:\n" + tup[1]

    messages.append({"role": "user", "content": content})

    completion = openai.ChatCompletion.create(
          model=model,
          messages=messages
    )

    chat_response = completion.choices[0].message.content

    generated_comments.append(chat_response)
    messages.append({"role": "assistant", "content": chat_response})
  
  
  code_blocks = [tup[1] for tup in blocks]

  return insert_comments(code, code_blocks, generated_comments)

  
#insert the comments we generated into the file
def insert_comments(file_contents, code_blocks, comments):
    modified_contents = file_contents
    
    for code_block, comment in zip(code_blocks, comments):
        
        comment_text = remove_markdown_code_block(comment)

        code_block_position = modified_contents.find(code_block)
        
        comment_text = f"\n\n{comment_text}\n"

        if code_block_position != -1:
            comment_insert_position = code_block_position
            
            modified_contents = (
                modified_contents[:comment_insert_position]
                + comment_text
                + modified_contents[comment_insert_position:]
            )
    
    return run_linter(modified_contents)


# This function is probably out of date, but we shouldn't need it for now
# Comment the given block of code
def comment_block(code, context=None, pred=None):
  
  # if no context was provided, we need to change the system prompt
  if context is None:
    messages = [
      {"role": "system", "content" : f"You're a C/C++ comment generator. You will generate a software comment in 50 words or less that summarizes the C/C++ code you are given. Focus on the practical aspects of the code's functionality and assume familiarity with C/C++ language concepts; avoid explaining basic syntax or standard data types."}
    ]

  else:
    messages = [
      {"role": "system", "content" : f"You're a C/C++ comment generator. You will generate a software comment in 50 words or less that summarizes the C/C++ code you are given. Focus on the practical aspects of the code's functionality and assume familiarity with C/C++ language concepts; avoid explaining basic syntax or standard data types."\
      "The code that you will be given will be from the following file: \n{context}"}
    ]

  # Find the code class and get the corresponding template-based prompt and combine them for our final prompt
  if pred is None:
    pred = int(classifier(code)[0]['label'][6:]) #get code class
  content = prompts[pred] + "\n\nCode:\n" + code
  messages.append({"role": "user", "content": content})

  # send it to chatGPT
  completion = client.chat.completions.create(
    model=model,
    messages=messages
  )

  # get the response and return it to the caller
  return completion.choices[0].message.content

# Comment file for a string rather than a file. str is a string containing the file to be commented.
def comment_file_str(str, decomp=""):
  # comment_file takes a filename, so we need to make a tempfile
  with tempfile.NamedTemporaryFile(mode='w', suffix='.c') as temp_file:
    temp_file.write(str)
    temp_file.flush()
    commented_file = comment_file(temp_file.name, decomp)
  
  return commented_file

if __name__ == "__main__":
  main()