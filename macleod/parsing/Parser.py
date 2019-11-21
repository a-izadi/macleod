import argparse
import logging
import os
import ply.lex as lex
import ply.yacc as yacc
import re

from pathlib import Path

import Ontology as Ontology
import logical.Logical as Logical
import logical.Connective as Connective
import logical.Logical as Logical
import logical.Negation as Negation
import logical.Quantifier as Quantifier
import logical.Symbol as Symbol

LOGGER = logging.getLogger(__name__)

tokens = (
    "LPAREN",
    "RPAREN",
    "NOT",
    "AND",
    "OR",
    "EXISTS",
    "FORALL",
    "IFF",
    "IF",
    "URI",
    "COMMENT",
    "CLCOMMENT",
    "STRING",
    "START",
    "IMPORT",
    "NONLOGICAL"
)

precedence = (('left', 'IFF'),
              ('left', 'IF'))


def t_NOT(t): r'not'; return t


def t_AND(t): r'and'; return t


def t_OR(t): r'or'; return t


def t_EXISTS(t): r'exists'; return t


def t_FORALL(t): r'forall'; return t


def t_IFF(t): r'iff'; return t


def t_IF(t): r'if'; return t


def t_CLCOMMENT(t): r'cl-comment'; return t


def t_START(t): r'cl-text'; return t


def t_IMPORT(t): r'cl-imports'; return t


def t_LPAREN(t): r'\('; return t


def t_RPAREN(t): r'\)'; return t


def t_error(t):
    print("Unknown character \"{}\"".format(t.value[0]))
    t.lexer.skip(1)


t_URI = r"http[s]?:\/\/(?:[a-zA-Z]|[0-9]|[$\=\?\/\%\-_@.&+]|[!*,]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
t_NONLOGICAL = r'[<>=\w\-=]+'
t_COMMENT = r'\/\*[\w\W\d*]+?\*\/'
t_STRING = r"'(.+?)'"
t_ignore = " \r\t\n"


def p_starter(p):
    """
    starter : COMMENT ontology
    starter : ontology
    """

    if len(p) == 3:

        p[0] = p[2]

    else:

        p[0] = p[1]


def p_ontology(p):
    """
    ontology : LPAREN START URI statement RPAREN
    ontology : statement
    """
    if len(p) == 6:

        p[0] = p[4]

    else:

        p[0] = p[1]


def p_ontology_error(p):
    """
    ontology : LPAREN START error
    ontology : LPAREN START URI error
    """

    if is_error(p.slice[3]):
        raise TypeError("Error in ontology: bad URI")

    raise TypeError("Error in ontology: bad statement")


def p_statement(p):
    """
    statement : axiom statement
    statement : import statement
    statement : comment statement
    statement : axiom
    statement : import
    statement : comment
    """

    if len(p) == 3:

        statements = [p[1]]

        if isinstance(p[2], list):
            statements += p[2]
        else:
            statements.append(p[2])

        p[0] = statements

    else:

        p[0] = [p[1]]


def p_comment(p):
    """
    comment : LPAREN CLCOMMENT STRING RPAREN
    """

    # p[0] = p[3]
    p[0] = None

def p_comment_error(p):
    """
    comment : LPAREN CLCOMMENT error RPAREN
    """

    if "'" not in p[3].value:
        raise TypeError("Error in comment: missing '")

    raise TypeError("Error in comment: bad string")


def p_import(p):
    """
    import : LPAREN IMPORT URI RPAREN
    """

    p[0] = p[3]

def p_import_error(p):
    """
    import : LPAREN IMPORT error
    """

    raise TypeError("Error in import: bad URI")

def p_axiom(p):
    """
    axiom : negation
          | universal
          | existential
          | conjunction
          | disjunction
          | conditional
          | biconditional
          | predicate
    """

    p[0] = p[1]


def p_negation(p):
    """
    negation : LPAREN NOT axiom RPAREN
    """

    p[0] = Negation.Negation(p[3])


def p_conjunction(p):
    """
    conjunction : LPAREN AND axiom_list RPAREN
    """

    p[0] = Connective.Conjunction(p[3])

def p_conjunction_error(p):
    """
    conjunction : LPAREN AND error
    """

    raise TypeError("Error in conjunction: bad axiom")

def p_disjunction(p):
    """
    disjunction : LPAREN OR axiom_list RPAREN
    """

    p[0] = Connective.Disjunction(p[3])

def p_disjunction_error(p):
    """
    disjunction : LPAREN OR error
    """

    raise TypeError("Error in disjunction: bad axiom")

def p_axiom_list(p):
    """
    axiom_list : axiom axiom_list
    axiom_list : axiom
    """

    if len(p) == 3:

        axioms = [p[1]]

        if isinstance(p[2], list):
            axioms += p[2]
        else:
            axioms.append(p[2])

        p[0] = axioms

    else:

        p[0] = [p[1]]


def p_conditional(p):
    """
    conditional : LPAREN IF axiom axiom RPAREN
    """

    p[0] = Connective.Disjunction([Negation.Negation(p[3]), p[4]])

def p_conditional_error(p):
    """
    conditional : LPAREN IF error
    conditional : LPAREN IF axiom error
    """

    if is_error(p.slice[3]):
        raise TypeError("Error in conditional: bad first axiom")

    raise TypeError("Error in conditional: bad second axiom")


def p_biconditional(p):
    """
    biconditional : LPAREN IFF axiom axiom RPAREN
    """

    p[0] = Connective.Conjunction([Connective.Disjunction([Negation.Negation(p[3]), p[4]]),
                                   Connective.Disjunction([Negation.Negation(p[4]), p[3]])
                                   ])


def p_biconditional_error(p):
    """
    biconditional : LPAREN IFF error
    biconditional : LPAREN IFF axiom error
    """

    if is_error(p.slice[3]):
        raise TypeError("Error in biconditional: bad first axiom")

    raise TypeError("Error in biconditional: bad second axiom")


def p_existential(p):
    """
    existential : LPAREN EXISTS LPAREN nonlogicals RPAREN axiom RPAREN
    """

    p[0] = Quantifier.Existential(p[4], p[6])

def p_existential_error(p):
    """
    existential : LPAREN EXISTS LPAREN error
    existential : LPAREN EXISTS LPAREN nonlogicals RPAREN error
    """

    if is_error(p.slice[4]):
        raise TypeError("Error in existential: bad nonlogical")

    raise TypeError("Error in existential: bad axiom")


def p_universal(p):
    """
    universal : LPAREN FORALL LPAREN nonlogicals RPAREN axiom RPAREN
    """

    p[0] = Quantifier.Universal(p[4], p[6])

def p_universal_error(p):
    """
    universal : LPAREN FORALL LPAREN error
    universal : LPAREN FORALL LPAREN nonlogicals RPAREN error
    """

    if is_error(p.slice[4]):
        raise TypeError("Error in universal: bad nonlogical")

    raise TypeError("Error in universal: bad axiom")

def p_predicate(p):
    """
    predicate : LPAREN NONLOGICAL parameter RPAREN
    """

    p[0] = Symbol.Predicate(p[2], p[3])

def p_predicate_error(p):
    """
    predicate : LPAREN NONLOGICAL error RPAREN
    """

    raise TypeError("Error in predicate: bad parameter")


def p_parameter(p):
    """
    parameter : function parameter
    parameter : nonlogicals parameter
    parameter : function
    parameter : nonlogicals
    """

    if len(p) == 3:

        if isinstance(p[1], list):
            parameters = p[1]
            if isinstance(p[2], list):
                parameters += p[2]
            else:
                parameters.append(p[2])
        else:
            parameters = [p[1]]
            if isinstance(p[2], list):
                parameters += p[2]
            else:
                parameters.append(p[2])

        p[0] = parameters

    else:

        if isinstance(p[1], list):
            p[0] = p[1]
        else:
            p[0] = [p[1]]


def p_function(p):
    """
    function : LPAREN NONLOGICAL parameter RPAREN
    """

    p[0] = Symbol.Function(p[2], p[3])

def p_function_error(p):
    """
    function : LPAREN NONLOGICAL error RPAREN
    """

    raise TypeError("Error in function: bad parameter")


def p_nonlogicals(p):
    """
    nonlogicals : NONLOGICAL nonlogicals
    nonlogicals : NONLOGICAL
    """

    if len(p) == 3:

        nonlogicals = [p[1]]

        if isinstance(p[2], list):
            nonlogicals += p[2]
        else:
            nonlogicals.append(p[2])

        p[0] = nonlogicals

    else:

        p[0] = [p[1]]


def p_error(p):
    global parser

    if p is None:
        raise TypeError("Unexpectedly reached EOF")

    # Note the location of the error before trying to lookahead
    error_pos = p.lexpos

    # A little stack manipulation here to get everything we need
    stack = [symbol for symbol in parser.symstack][1:]
    length = len(stack)

    index_current_axiom = next((stack.index(x) for x in stack[::-1] if x.type == 'axiom'), len(stack))
    current_axiom = stack[index_current_axiom:]
    current_axiom.append(p)

    # Use the brace level to figure out how many future tokens we need to complete the error token
    lparens = len([x for x in current_axiom if x.type == "LPAREN"])


    lookahead_tokens = []
    while lparens != 0:
        lookahead_token = parser.token()
        if lookahead_token is None:
            break
        else:
            lookahead_tokens.append(lookahead_token)
            if lookahead_token.type == "RPAREN":
                lparens -= 1
            elif lookahead_token.type == "LPAREN":
                lparens += 1

    # Put together a full list of tokens for the error token
    current_axiom += lookahead_tokens

    # String manipulation to "underbar" the error token
    axiom_string = []
    overbar_error = ''.join([x+'\u0332' for x in p.value])
    p.value = overbar_error

    for token in current_axiom:
        raw_token = token.value
        if isinstance(raw_token, str):
            axiom_string.append(raw_token + ' ')
        elif isinstance(raw_token, list):
            for sub_token in raw_token:
                axiom_string.append(sub_token + ' ')

    string_up_to_error = p.lexer.lexdata[:error_pos]
    types = [symbol.type for symbol in stack]
    print("""Error at line {}! Unexpected Token: '{}' :: "{}"\n\n{}""".format(
        string_up_to_error.count("\n"),
        p.value,
        ''.join(axiom_string),
        ' '.join(types)))

    return p


def parse_file(path, sub, base, resolve=False, name=None):
    """
    Accepts a path to a Common Logic file and parses it to return an Ontology object.

    :param path, path to common logic file
    :param sub, path component to be substituted
    :param base, new path component
    :param resolve, resolve imports?
    :param name, for overriding the default naming
    :return Ontology onto, newly constructed ontology object
    """

    path = os.path.normpath(os.path.join(base, path))

    if not os.path.isfile(path):
        LOGGER.warning("Attempted to parse non-existent file: " + path)
        return None

    ontology = Ontology.Ontology(path)

    if name is not None:
        ontology.name = name


    with open(path, 'r') as f:
        buff = f.read()

    if not buff:
        return None

    lex.lex(reflags=re.UNICODE)
    global parser
    parser = yacc.yacc()

    parsed_objects = yacc.parse(buff)


    ontology.basepath = (sub, base)

    for logical_thing in parsed_objects:

        if isinstance(logical_thing, Logical.Logical):

            ontology.add_axiom(logical_thing)

        elif isinstance(logical_thing, str):

            ontology.add_import(logical_thing)

    if resolve:

        ontology.resolve_imports(resolve)

    return ontology


def get_line_number(string, pos):
    return string[:pos].count('\n') + 1


def is_error(obj):
    return isinstance(obj, yacc.YaccSymbol) and obj.type == "error"


if __name__ == '__main__':

    # Support conditional parameters
    import sys

    parser = argparse.ArgumentParser(description='Utility function to read and translate Common Logic Interchange Format (.clif) files.')
    parser.add_argument('-f', '--file', type=str, help='Path to Clif file to parse', required=True)
    parser.add_argument('-p', '--ffpcnf', action="store_true", help='Automatically convert axioms to function-free prenex conjuntive normal form', default=False)
    parser.add_argument('--resolve', action="store_true", help='Automatically resolve imports', default=False)
    parser.add_argument('-b', '--base', required='--resolve' in sys.argv, type=str, help='Path to directory containing ontology files')
    parser.add_argument('-s', '--sub', required='--resolve' in sys.argv, type=str, help='String to replace with basepath found in imports')
    args = parser.parse_args()

    LOGGER.warning("DERP")
    ontology = parse_file(args.file, args.sub, args.base, args.resolve)
    pretty_print(ontology, args.ffpcnf)
