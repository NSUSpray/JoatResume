"""Command line launcher"""

import argparse as ap
from pathlib import Path

from app import load_yaml, render


def get_parser() -> ap.ArgumentParser:
    parser = ap.ArgumentParser()
    add = parser.add_argument
    add('data',
            help = 'YAML file or directory with the applicant data.',
            metavar = '<path>')
    add('-p', '--position',
            nargs = '+',
            help = 'Title(s) of the position in English and rest languages.',
            metavar = '<title>')
    add('-s', '--specs',
            nargs = '+',
            default = [],
            help = 'Specializations.',
            metavar = '<spec>')
    add('-l', '--language',
            default = 'en',
            help = 'Language to select. For example: -l ru. Default: en',
            metavar = '<language>')
    add('--style',
            action = 'extend',
            default = [],
            nargs = '+',
            help = 'CSS files with additional styles.',
            metavar = '<file>')
    add('-t', '--templates',
            action = 'extend',
            default = [],
            nargs = '+',
            help = 'Custom template directories.'
                    ' The directories will be searched in order,'
                    ' stopping at the last matched template.',
            metavar = '<directory>')
    add('--titles',
            help = 'YAML file with custom titles.',
            metavar = '<file>')
    add('-o', '--out',
            help = 'File to save the result to.',
            metavar = '<file>')
    return parser


def load_data(data_path: Path, positions: list[str]) -> dict:
    if data_path.is_dir:
        data = {}
        for path in data_path.glob('*.yaml'):
            data.update(load_yaml(path))
    else:
        data = load_yaml(data_path)  # TODO: exsists?
    if positions:
        if len(positions) >= 2:
            data['position'] = { 'en': positions[0], 'ru': positions[1] }
        else:
            data['position'] = positions[0]
    return data


def main() -> None:
    parser = get_parser()
    args = parser.parse_args()
    data_path = Path(args.data)
    style = '\n'.join(Path(s).read_text(encoding='utf-8') for s in args.style)  # TODO: exsist?
    settings = {}
    for path in args.templates:
        settings_path = Path(path, 'settings.yaml')
        if settings_path.exists():
            settings.update(load_yaml(settings_path))
    titles = load_yaml(args.titles) if args.titles else {}  # TODO: exsists?
    rendered, data = render(
        load_data(data_path, args.position),
        args.specs,
        args.language,
        style,
        reversed(args.templates),
        settings,
        titles,
    )
    filename = args.out or f'{data['surname']} - {data['position']}.html'
    Path(filename).write_text(rendered, encoding='utf-8')


main()
