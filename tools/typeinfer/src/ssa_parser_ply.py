import ply.lex as lex
import ply.yacc as yacc
from ssa_objects import Instruction, Variable, Constant, FunctionCall
from loguru import logger
from utils import time_it


tokens = (
    'INT', 'HEX_LITERAL', 'VARIABLE', 'CONSTANT', 'IDENTIFIER',
    'LBRACK', 'RBRACK', 'COLON', 'ASSIGN', 'LPAREN', 'RPAREN', 'COMMA',
    'PHI'
)
t_ignore = ' \t'
t_LBRACK = r'\[';
t_RBRACK = r'\]';
t_COLON = r':';
t_ASSIGN = r'='
t_LPAREN = r'\(';
t_RPAREN = r'\)';
t_COMMA = r','
t_PHI = r'𝛟'


def t_HEX_LITERAL(t): r'0x[0-9a-fA-F]+'; return t


def t_CONSTANT(t): r'\$0x[0-9a-fA-F]+'; t.value = Constant(t.value); return t


def t_VARIABLE(t): r'v\d+'; t.value = Variable(t.value); return t


def t_IDENTIFIER(t): r'[a-zA-Z_][a-zA-Z_0-9]*'; return t


def t_INT(t): r'\d+'; t.value = int(t.value); return t


def t_newline(t): r'\n+'; t.lexer.lineno += len(t.value)


def t_error(t): logger.error(f"Illegal character '{t.value[0]}' on line {t.lexer.lineno}"); t.lexer.skip(1)

def t_COMMENT(t):
    r'\#.*'
    pass

lexer = lex.lex()


# --- (Parser) ---

def p_line(p):
    '''line : instruction
            | phi_instruction'''
    p[0] = p[1]


def p_instruction(p):
    '''instruction : INT LBRACK HEX_LITERAL RBRACK COLON expression'''
    expr_info = p[6]
    p[0] = Instruction(
        inst_id=p[1], address=p[3], operation=expr_info['op'],
        output=expr_info['output'], args=expr_info['args']
    )


def p_phi_instruction(p):
    '''phi_instruction : VARIABLE ASSIGN PHI LPAREN arg_list RPAREN'''
    line_num = p.lineno(1)
    p[0] = Instruction(
        inst_id=-line_num, address="phi_node", operation="Phi",
        output=p[1], args=p[5]
    )


def p_expression(p):
    '''expression : assignment
                  | value_expression'''
    p[0] = p[1]


def p_assignment(p):
    '''assignment : VARIABLE ASSIGN value'''
    value_info = p[3]
    value_info['output'] = p[1]
    p[0] = value_info


def p_value_expression(p):
    '''value_expression : value'''
    value_info = p[1]
    value_info['output'] = None
    p[0] = value_info


def p_value(p):
    '''value : function_call
             | standalone_value'''
    if isinstance(p[1], FunctionCall):
        p[0] = {'op': p[1].name, 'args': p[1].args}
    else:
        p[0] = p[1]


def p_function_call(p):
    '''function_call : IDENTIFIER LPAREN arg_list RPAREN
                     | IDENTIFIER LPAREN RPAREN'''
    op_name = p[1]
    args = []
    if len(p) == 5:
        args = p[3]
    p[0] = FunctionCall(op_name, args)


def p_standalone_value(p):
    '''standalone_value : VARIABLE
                        | CONSTANT
                        | IDENTIFIER'''
    if isinstance(p[1], (Variable, Constant)):
        p[0] = {'op': 'Assign', 'args': [p[1]]}
    else:
        p[0] = {'op': p[1], 'args': []}


def p_arg_list(p):
    '''arg_list : arg_list COMMA arg
                | arg'''
    p[0] = p[1] + [p[3]] if len(p) == 4 else [p[1]]



def p_arg(p):
    '''arg : any_constant
           | VARIABLE
           | function_call
           | INT'''
    p[0] = p[1]


def p_any_constant(p):
    '''any_constant : CONSTANT
                    | HEX_LITERAL'''
    p[0] = Constant(p[1]) if isinstance(p[1], str) else p[1]


def p_error(p):
    pass


parser = yacc.yacc(start='line', debug=False)