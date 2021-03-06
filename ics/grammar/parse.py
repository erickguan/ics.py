import collections
from pathlib import Path
from typing import Dict, List

import attr
import tatsu
from tatsu.exceptions import FailedToken

from ics.types import ContainerItem, RuntimeAttrValidation

grammar_path = Path(__file__).parent.joinpath('contentline.ebnf')

with open(grammar_path) as fd:
    GRAMMAR = tatsu.compile(fd.read())


class ParseError(Exception):
    pass


@attr.s(repr=False)
class ContentLine(RuntimeAttrValidation):
    """
    Represents one property line.

    For example:

    ``FOO;BAR=1:YOLO`` is represented by

    ``ContentLine('FOO', {'BAR': ['1']}, 'YOLO'))``
    """

    name: str = attr.ib(converter=str.upper)  # type: ignore
    params: Dict[str, List[str]] = attr.ib(factory=dict)
    value: str = attr.ib(default="")

    def __str__(self):
        params_str = ''
        for pname in self.params:
            params_str += ';{}={}'.format(pname, ','.join(self.params[pname]))  # TODO ensure escaping?
        return "{}{}:{}".format(self.name, params_str, self.value)

    def __repr__(self):
        return "<ContentLine '{}' with {} parameter{}. Value='{}'>".format(
            self.name,
            len(self.params),
            "s" if len(self.params) > 1 else "",
            self.value,
        )

    def __getitem__(self, item):
        return self.params[item]

    def __setitem__(self, item, *values):
        self.params[item] = list(values)

    @classmethod
    def parse(cls, line):
        """Parse a single iCalendar-formatted line into a ContentLine"""
        if "\n" in line or "\r" in line:
            raise ValueError("ContentLine can only contain escaped newlines")
        try:
            ast = GRAMMAR.parse(line)
        except FailedToken:
            raise ParseError()
        else:
            return cls.interpret_ast(ast)

    @classmethod
    def interpret_ast(cls, ast):
        name = ''.join(ast['name'])
        value = ''.join(ast['value'])
        params = {}
        for param_ast in ast.get('params', []):
            param_name = ''.join(param_ast["name"])
            param_values = [''.join(x) for x in param_ast["values_"]]
            params[param_name] = param_values
        return cls(name, params, value)

    def clone(self):
        """Makes a copy of itself"""
        return attr.evolve(self)


class Container(List[ContainerItem]):
    """Represents an iCalendar object.
    Contains a list of ContentLines or Containers.

    Args:

        name: the name of the object (VCALENDAR, VEVENT etc.)
        items: Containers or ContentLines
    """

    def __init__(self, name: str, *items: ContainerItem):
        self.check_items(*items)
        super(Container, self).__init__(items)
        self.name = name

    def __str__(self):
        name = self.name
        ret = ['BEGIN:' + name]
        for line in self:
            ret.append(str(line))
        ret.append('END:' + name)
        return "\r\n".join(ret)

    def __repr__(self):
        return "<Container '{}' with {} element{}>" \
            .format(self.name, len(self), "s" if len(self) > 1 else "")

    @classmethod
    def parse(cls, name, tokenized_lines):
        items = []
        for line in tokenized_lines:
            if line.name == 'BEGIN':
                items.append(cls.parse(line.value, tokenized_lines))
            elif line.name == 'END':
                if line.value != name:
                    raise ParseError(
                        "Expected END:{}, got END:{}".format(name, line.value))
                break
            else:
                items.append(line)
        return cls(name, *items)

    def clone(self):
        """Makes a copy of itself"""
        return self.__class__(self.name, *self)

    def check_items(self, *items):
        from ics.utils import check_is_instance
        if len(items) == 1:
            check_is_instance("item", items[0], (ContentLine, Container))
        else:
            for nr, item in enumerate(items):
                check_is_instance("item %s" % nr, item, (ContentLine, Container))

    def __setitem__(self, index, value):
        self.check_items(value)
        super(Container, self).__setitem__(index, value)

    def insert(self, index, value):
        self.check_items(value)
        super(Container, self).insert(index, value)

    def append(self, value):
        self.check_items(value)
        super(Container, self).append(value)

    def extend(self, values):
        self.check_items(*values)
        super(Container, self).extend(values)

    def __add__(self, values):
        container = type(self)(self.name)
        container.extend(self)
        container.extend(values)
        return container

    def __iadd__(self, values):
        self.extend(values)
        return self


def unfold_lines(physical_lines):
    if not isinstance(physical_lines, collections.abc.Iterable):
        raise ParseError('Parameter `physical_lines` must be an iterable')
    current_line = ''
    for line in physical_lines:
        if len(line.strip()) == 0:
            continue
        elif not current_line:
            current_line = line.strip('\r')
        elif line[0] in (' ', '\t'):
            current_line += line[1:].strip('\r')
        else:
            yield current_line
            current_line = line.strip('\r')
    if current_line:
        yield current_line


def tokenize_line(unfolded_lines):
    for line in unfolded_lines:
        yield ContentLine.parse(line)


def parse(tokenized_lines):
    # tokenized_lines must be an iterator, so that Container.parse can consume/steal lines
    tokenized_lines = iter(tokenized_lines)
    res = []
    for line in tokenized_lines:
        if line.name == 'BEGIN':
            res.append(Container.parse(line.value, tokenized_lines))
        else:
            res.append(line)
    return res


def lines_to_container(lines):
    return parse(tokenize_line(unfold_lines(lines)))


def string_to_container(txt):
    return lines_to_container(txt.splitlines())


def calendar_string_to_containers(string):
    if not isinstance(string, str):
        raise TypeError("Expecting a string")
    return string_to_container(string)
