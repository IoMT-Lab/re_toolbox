from agent4decompile.pipeline import Agent4DecompilePipeline
import sys
import os
import tempfile

local_path = os.path.dirname(__file__)
sys.path.append(local_path)


def main():
    try:
        filepath = sys.argv[1]
        pipeline = Agent4DecompilePipeline()

        temp_dir = tempfile.mkdtemp()
        result = pipeline.run(binary_path=filepath, output_dir=temp_dir)

        if 'refined' not in result.output_files:
            exit(1)
        else:
            print(result.output_files['refined'])
            exit(0)
    except Exception as e:
        print(str(e), file=sys.stderr)
        exit(1)


if __name__ == '__main__':
    main()
