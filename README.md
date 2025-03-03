# JoatResume — flexible résumé generator

Multilingual résumé generator with filtering and sorting achievements, skills, etc. by qualifications in them and by the applicant’s specialization. A handy tool for generating special résumé for various vacancies based on complete data about the specialist.

## Install

Create a virtualenv, activate it, and run:
```shell
pip install -r JoatResume/requirements.txt
```

## Prepare data

Make a directory and create one or more YAML files in it with the information about the person (see example in the *JoatResume/example/data* directory). You can put all the data in one file or split it into several files. The files must have the *.yaml* extension, file names don’t matter.

## Usage examples

Render the example applicant data, specifying the position title, selecting the *back-end* specialization, and saving the result in the *output.html* file:

```shell
python JoatResume JoatResume/example/data -p "Back-end Engineer" -s back-end -o output.html
```

Render data from the *petrov* directory, specifying the position title in English and Russian, selecting the *game* and *python* specializations, using Russian language, and saving the result file in the current directory with the default name:

```shell
python JoatResume petrov -p "Game Developer" "Разработчик игр" -s game python -l ru
```

See the information about all the options:

```shell
python JoatResume --help
```

## Advanced usage

You can apply one or more custom CSS, custom titles, or use custom Jinja templates:

```shell
python JoatResume data --style style1.css style2.css --templates templates --titles titles.yaml
```

The custom styles will be applied in addition to the base style: the last styles will be applied on top of the first ones. You can override one, some, or all of the default Jinja templates that are in the *JoatResume/templates* directory.

## Run doctest tests

```shell
python -m doctest -v JoatResume/app.py
```
