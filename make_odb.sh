#!/bin/bash


cd ./odb/

zip -0 Template.zip mimetype

zip -r Template.zip *

cd ..

mv ./odb/Template.zip ./CloudContactOOo/hsqldb/Template.odb
