#!/bin/bash

docker run --rm -it -v"`pwd`/graph":/tmp/GraphAnalysis -v"`pwd`/struct":/tmp/structanalysis re_toolbox:latest