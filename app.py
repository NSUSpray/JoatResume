import copy
import datetime as dt
import functools as ft
import locale as l
import math as m
import operator as o
from pathlib import Path
import re
import typing as t

import jinja2 as j2
import pendulum as p
import yaml


Lang = t.Literal['ru', 'en']
Skill = tuple[str, dict]


URL_PATTERN = re.compile('^(https?:\\/\\/)?(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]'
        '{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$')

TIMEZONES: dict[Lang, str | p.Timezone]
TIMEZONES = { 'ru': 'Europe/Moscow', 'en': p.UTC }

LANGUAGES: set[Lang] = {'ru', 'en'}


def load_yaml(filename: str | Path) -> dict:
    """
    Open file, parse the first YAML document in the stream, and produce the
    corresponding Python object.
    """
    with open(filename, encoding='utf-8') as file:
        data = yaml.load(file, Loader=yaml.FullLoader)
    return data or {}


def within_package(filename: str | Path) -> Path:
    """Return path to the the given file by path relative to the package root.

    :param filename: A file path to find within the package.

    >>> within_package('templates/skills.jinja').is_file()
    True
    >>> within_package('cartoons/Shrek.mp4').is_file()
    False
    """
    return Path(Path(__file__).parent, filename)


def get_env(*searchpath: str | Path, user_settings: dict) -> j2.Environment:
    """
    Return a Jinja environment object with the necessary filters and globals.

    :param searchpath:
        A list of paths to the directories, that contains the templates. The
        directories will be searched in order, stopping at the first matching
        template.
    :param user_settings:
        Values to update the dictionary of environment globals.
    """
    env = j2.Environment(
        loader=j2.FileSystemLoader(searchpath),
        autoescape=j2.select_autoescape(),
    )

    def env_filter(func: t.Callable) -> t.Callable:
        """Add a function to the environment’s filters dictionary."""
        env.filters[func.__name__] = func
        return func

    def env_global(func: t.Callable) -> t.Callable:
        """Add a function to the environment’s globals dictionary."""
        env.globals[func.__name__] = func
        return func

    @env_filter
    def a_(link: str, text='', trim=False) -> str:
        """Render an anchor element with the specified href and text.

        :param link: A link for the href attribute.
        :param text: A text for the anchor element.
            If it is not specified, then the link is used as the anchor text.
        :param trim: Trim “https://”, “www.”, and trailing “/” in the text.

        >>> 'johndoe@example.com' | a_('Mail me')
        '<a href="mailto:johndoe@example.com" class="texted-link">Mail me</a>'
        >>> 'https://www.example.com/' | a_(trim=True)
        '<a href="https://www.example.com/">example.com</a>'
        """
        attrs = ''
        if text:
            attrs += ' class="texted-link'
            if URL_PATTERN.match(text):
                attrs += ' text-is-link'
            attrs += '"'
        if not text:
            text = link
        if trim:
            text = re.sub(r'^(https?://)?(www\.)?(.+?)/?$', r'\3', text)
        if '@' in link:
            link = 'mailto:' + link
        return f'<a href="{link}"{attrs}>{text}</a>'

    @env_filter
    def experience_boundary(date: dt.date, fmt: str, locale: Lang) -> str:
        """
        Return a string representing the date, controlled by an explicit
        format string and locale.
        
        :param date: An object to represent.
        :param fmt: A style string used by the `date`.strftime() method.
        :param locale: A locale set before calling strftime().
        """
        l.setlocale(l.LC_ALL, locale)
        result = date.strftime(fmt)
        l.setlocale(l.LC_ALL, '')
        return result.capitalize()

    # TODO: maybe you should use itertools.groupby instead
    @env_filter
    def group_by(skills: dict[str, dict], path: list[str], min_size=0) -> dict:
        """Group `skills` by values at the specified `path`.

        :param skills: A skill dictionary to group.
        :param path:
            A list of keys for getting the values by which to group skills.
        :param min_size:
            If several groups are smaller than `min_size`, then combine them
            into the “other” group.
        """
        grouped = {}
        for name, details in skills.items():
            dest_value = ft.reduce(o.getitem, path, details)
            group_name = dest_value
            if group_name not in grouped:
                grouped[group_name] = {}
            new_details = copy.deepcopy(details)
            dest_mapping = ft.reduce(o.getitem, path[:-1], new_details)
            dest_mapping.pop(path[-1])
            grouped[group_name][name] = new_details

        small_groups = { group_name: skills
                for group_name, skills in grouped.items()
                        if len(skills) < min_size }
        if len(small_groups) > 1:
            combined_group_name = \
                    'all' if len(small_groups) == len(grouped) else 'other'
            grouped[combined_group_name] = {}
            for group_name, skills in small_groups.items():
                grouped[combined_group_name].update(skills)
                grouped.pop(group_name)

        return grouped

    @env_filter
    def phone(num: str, group='()', sep='‒') -> str:
        """
        Format a phone number using the specified characters to group and
        separate digits.

        :param num: A raw phone number.
        :param group: Symbols for grouping three digits after the country code.
        :param sep: A separator between the other groups of digits.

        >>> '+12 3456789012' | phone(group='[]', sep='_')
        '+12 [345] 678_90_12'
        """
        if group:
            num = re.sub(r' (\d{3})', rf' {group[0]}\1{group[1]} ', num)
        if sep:
            num = re.sub(r'(\d\d)(\d\d)$', rf'{sep}\1{sep}\2', num)
        return num

    @env_filter
    def sort_by_priority(
            skills: list[Skill],
            selected_specs: list[str] = []) -> list[Skill]:
        """
        Return a new list containing all items from the `skills` in the order
        determined by 1) the specializations order and 2) the skill attributes.

        :param skills: A list of sorting skills.
        :param selected_specs: Specializations in descending order of priority.

        >>> [('a', {}), ('b', {}), ('a', {})] | sort_by_priority(['b', 'a'])
        [('b', {}), ('a', {}), ('a', {})]
        """
        def key_(skill: Skill) -> tuple[float, float]:
            name, details = skill
            specs: list[str] = details.get('specializations', [])
            spec_order = -sum(m.exp(-selected_specs.index(s))
                    for s in specs if s in selected_specs)
            attr_order = -m.prod(details['attributes'].values())
            return spec_order, attr_order
        return sorted(skills, key=key_)

    @env_global
    def duration(
            from_: dt.date,
            to: dt.date,
            locale: Lang | None = None) -> str:
        """
        Return the difference between two dates as a string using the specified
        locale.

        :param from_: A date to compare from.
        :param to: A date to compare to (defaults to today).
        :param locale: A locale to use. Defaults to current locale.
        """
        to = p.instance(to) if to else p.today().date()
        to += p.duration(months=1)
        words = to.diff(from_).in_words(locale, '#').split('#')
        words = [w for w in words if not re.match(r'\d+\s+[wdнд]', w)]
        return ' '.join(words)

    @env_global
    def now(fmt: str, locale: Lang | None = None) -> str:
        """Get a current date as a string using the given format.

        :param fmt: A format to use.
        :param locale: A locale to use. Defaults to current locale.
        """
        return p.now(TIMEZONES[locale or 'en']).format(fmt, locale)

    settings = load_yaml(within_package('templates/settings.yaml'))
    env.globals.update(settings | user_settings)

    return env


def filter_specs(data: dict, specs: list[str]) -> dict:
    """
    Return a filtered copy of the applicant’s data containing values only from
    the `specs` list.

    :param data: A dictionary with the applicant data.
    :param specs: A list of specializations.
    """
    data = data.copy()
    if not specs: return data

    specs_set = set(specs)
    def match_skill(details: dict):
        return 'specializations' not in details \
                or set(details['specializations']) & specs_set
    data['skills'] = { skill: details
            for skill, details in data['skills'].items()
                    if match_skill(details) }

    remain_skills = {skill for skill, details in data['skills'].items()
            if 'specializations' in details}
    def match_item(item: dict):
        return 'skills' not in item \
                or set(item['skills']) & remain_skills
    def filter_crtfctns(crtfctns: list[dict]) -> list[dict]:
        return [certificate for certificate in crtfctns
                if match_item(certificate)]
    for key in ('experience', 'projects'):
        data[key] = [item for item in data[key] if match_item(item)]
    data['certifications'] = { year: filtered
            for year, crtfctns in data['certifications'].items()
                if (filtered := filter_crtfctns(crtfctns)) }

    return data


def filter_lang(data: dict, lang: Lang) -> dict:
    """
    Return a filtered copy of the applicant’s data containing values only of
    the specified language.

    :param data: A dictionary with the applicant data.
    :param lang: A string containing the language code, e. g. 'en'.

    >>> filter_lang({ 'skills': [{ 'en': 'Skills', 'ru': 'Навыки' }] }, 'en')
    {'skills': ['Skills']}
    """
    def fl(d):
        match d:
            case dict():
                if set(d) <= LANGUAGES:
                    return fl(d[lang]) if lang in d else None
                else:
                    return { key: fl(value) for key, value in d.items() }
            case list():
                return [fl(value) for value in d]
            case _:
                return d
    result = fl(data)
    assert isinstance(result, dict)
    return result


def render(
        data: dict,
        specs: list[str] = [],
        lang: Lang = 'en',
        style = '',
        template_dirs: t.Iterable[str | Path] = [],
        settings = {},
        titles: dict = {},
        ) -> tuple[str, dict]:
    """Return a tuple of the rendered template and the rendering data.

    :param data: A dictionary with the applicant data.
    :param specs: A list of specializations.
    :param lang: A string containing the language code, e. g. 'en'.
    :param style: An additional CSS style.
    :param template_dirs:
        A list of additional paths to the directories, that contains the
        templates. The directories will be searched in order, stopping at the
        first matching template.
    :param settings: Values to update the dictionary of environment globals.
    :param titles: Custom titles for template.
    """

    env = get_env(*template_dirs, within_package('templates'),
            user_settings=settings)
    template = env.get_template('__html__.jinja')

    titles = load_yaml(within_package('titles.yaml')) | titles
    base_style = within_package('style.css').read_text(encoding='utf-8')
    completed = data | { 'titles': titles, 'style': base_style + style }
    filtered = filter_specs(completed, specs)
    filtered = filter_lang(filtered, lang)
    final = filtered | { 'selected_specs': specs, 'language': lang }

    rendered = template.render(final)
    cleaned = re.sub(r'(?m)^\s+$', '', rendered)  # delete lines of spaces
    cleaned = re.sub(r'\n{2,}', '\n', cleaned).strip()  # delete empty lines
    enriched = re.sub(r'\s—(\s)', '\N{nbsp}—\\1', cleaned)
    return enriched, filtered
