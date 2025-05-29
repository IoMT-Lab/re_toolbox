import ast
import networkx as nx
import matplotlib.pyplot as plt
import os
import json

def run_graph_analysis(input_file_path):
    output_dir = "/tmp/GraphAnalysis"
    os.makedirs(output_dir, exist_ok=True)

    input_graph = []
    print(f"Attempting to read file: {input_file_path}")
    line_num = 0
    try:
        with open(input_file_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line_num += 1
                cleaned_line = line.strip().rstrip(',').strip()

                if not cleaned_line:
                    continue
                try:
                    item = ast.literal_eval(cleaned_line)
                    if isinstance(item, list):
                        input_graph.append(item)
                    else:
                        print(f"Warning: Line {line_num} '{line.strip()}' was successfully parsed but is not a list type ({type(item).__name__}), skipped.")
                except (ValueError, SyntaxError) as e:
                    print(f"Error: Line {line_num} could not be parsed as a Python list. Original content: '{line.strip()}'. Processed content: '{cleaned_line}'. Error: {e}")
                    continue
                except Exception as e:
                    print(f"Unknown error: Line {line_num} failed to process. Original content: '{line.strip()}'. Processed content: '{cleaned_line}'. Error: {e}")
                    continue
    except FileNotFoundError:
        print(f"Error: Input file '{input_file_path}' not found.")
        return
    except Exception as e:
        print(f"An unexpected error occurred while reading the input file: {e}")
        return

    print(f"File reading complete. Successfully parsed {len(input_graph)} sequences.")
    if not input_graph:
        print("No access sequences were successfully parsed. Please check the input file format or its content.")
        return

    input_file_name_base = os.path.basename(input_file_path)

    G = nx.DiGraph()

    for seq in input_graph:
        if not seq:
            continue
        first = seq[0]
        if isinstance(first, int) and (first % 8) == 0 and (first <= 400):
            if first <= 0:
                src = "base"
            else:
                src = f"base_{first}"
                G.add_edge("base", src)
        else:
            src = str(first)
            G.add_edge("base", src)

        for node in seq[1:]:
            if isinstance(node, int) and node % 8 == 0 and node <= 400:
                dst = f"base_{node}"
            else:
                dst = str(node)
            G.add_edge(src, dst)
            src = dst

    person_nodes = [n for n in G.nodes if str(n).startswith("base")]

    if not G.nodes():
        print("The graph is empty. Cannot perform centrality analysis.")
        social_analysis = {}
    else:
        closeness = nx.closeness_centrality(G)
        betweenness = nx.betweenness_centrality(G)
        pagerank = nx.pagerank(G)
        degree = nx.degree_centrality(G)

        social_analysis = {}
        for node in person_nodes:
            social_analysis[node] = {
                "closeness": closeness.get(node, 0),
                "betweenness": betweenness.get(node, 0),
                "pagerank": pagerank.get(node, 0),
                "degree": degree.get(node, 0)
            }

    if not social_analysis:
        print("No 'base' nodes found for analysis.")
    else:
        for person, metrics in social_analysis.items():
            print(f"Node: {person}")
            for metric, value in metrics.items():
                print(f"  {metric}: {value:.4f}")
            print()

    analysis_json_path = os.path.join(output_dir, f"{input_file_name_base}_analysis.json")
    with open(analysis_json_path, 'w', encoding='utf-8') as f:
        json.dump(social_analysis, f, indent=4)
    print(f"Graph analysis results (centrality) saved to: {analysis_json_path}")

    adjacency_list_path = os.path.join(output_dir, f"{input_file_name_base}_adjacency_list.txt")
    with open(adjacency_list_path, 'w', encoding='utf-8') as f:
        if G.nodes():
            for line in nx.generate_adjlist(G):
                f.write(line + '\n')
        else:
            f.write("# Graph is empty, no adjacency list to display.\n")
    print(f"Graph adjacency list saved to: {adjacency_list_path}")

    base_nodes_list_path = os.path.join(output_dir, f"{input_file_name_base}_base_nodes.json")
    with open(base_nodes_list_path, 'w', encoding='utf-8') as f:
        json.dump(sorted(person_nodes), f, indent=4)
    print(f"Identified 'base_xx' nodes saved to: {base_nodes_list_path}")

    adjacency_list_content = ""
    if os.path.exists(adjacency_list_path):
        with open(adjacency_list_path, 'r', encoding='utf-8') as f:
            adjacency_list_content = f.read()
    else:
        adjacency_list_content = "# Adjacency list file not generated or empty."

    analysis_json_content = ""
    if os.path.exists(analysis_json_path):
        with open(analysis_json_path, 'r', encoding='utf-8') as f:
            analysis_json_content = f.read()
    else:
        analysis_json_content = "{}"

    base_nodes_content = ""
    if os.path.exists(base_nodes_list_path):
        with open(base_nodes_list_path, 'r', encoding='utf-8') as f:
            base_nodes_content = f.read()
    else:
        base_nodes_content = "[]"

    llm_prompt_path = os.path.join(output_dir, f"{input_file_name_base}_schema_inference_prompt.txt")
    with open(llm_prompt_path, 'w', encoding='utf-8') as f:
        prompt_content = f"""As an expert in data structures, graph theory, and reverse engineering, I need your assistance in inferring the nature of an underlying data structure based on its access patterns.

I have performed an analysis on a series of access sequences, which were then used to construct a directed graph representing these patterns. I've extracted several key pieces of information from this graph.

Here is the data for your analysis:

---
**1. Graph Adjacency List:**
{adjacency_list_content.strip()}

---
**2. Centrality Analysis Results for 'base' Nodes (JSON Format):**
```json
{analysis_json_content.strip()}
```
**3. Identified 'base' Nodes (JSON Format):**
{base_nodes_content.strip()}

Based on the provided data, please attempt to infer the following:

Most Likely Data Structure Type:

What type of underlying data structure do these access patterns suggest? (e.g., Array, Linked List, Tree (Binary, N-ary), Hash Table, Struct/Record, Graph, Stack, Queue, etc.)
Justify your reasoning based on the access sequences, graph connectivity, and node characteristics (especially the "base_XX" pattern).

Inferred Field Names/Offsets (or relevant components):

Considering the 'base' and 'base_XX' nodes, what are the most probable "field names" or "component identifiers" within the inferred structure?
For each inferred field/component, provide its name (e.g., offset_0, field_8, status_code, etc.) and a brief explanation of what it might represent based on its connections or numerical values (e.g., base_8 could represent an integer field at offset 8 bytes).
Explain how these relate to the graph nodes (e.g., base_8 node in the graph corresponds to field_at_offset_8).

Potential Semantics/Purpose:

What might be the general purpose or typical use case of such a structure given its access patterns and inferred fields? (e.g., representing a CPU register context, a network packet header, a game object's properties, etc.) This is a more speculative inference.

Please provide your analysis in a structured and clear markdown format.
"""
        f.write(prompt_content)
    print(f"LLM prompt for schema inference saved to: {llm_prompt_path}")

    if G.nodes():
        pos = nx.spring_layout(G, seed=42)
        plt.figure(figsize=(12, 8))
        nx.draw(
            G, pos,
            with_labels=True,
            node_size=1000,
            font_size=8,
            node_color='lightblue',
            edge_color='gray',
            arrows=True,
            arrowsize=10,
        )
        plt.title("Access Pattern Graph")
        plt.axis("off")
        plt.show()
    else:
        print("The graph is empty. Cannot visualize.")

if __name__ == "__main__":
    input_dir = "/tmp/structanalysis"
    if not os.path.exists(input_dir):
        print(f"Directory {input_dir} does not exist.")
    else:
        for filename in os.listdir(input_dir):
            if filename.endswith(".txt"):
                input_path = os.path.join(input_dir, filename)
                run_graph_analysis(input_path)
