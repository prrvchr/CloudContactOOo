#!/bin/bash

./make_rdb.sh

cd ./CloudContactOOo/

zip -0 CloudContactOOo.zip mimetype

zip -r CloudContactOOo.zip *

cd ..

mv ./CloudContactOOo/CloudContactOOo.zip ./CloudContactOOo.oxt
