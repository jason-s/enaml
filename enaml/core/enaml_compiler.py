#------------------------------------------------------------------------------
#  Copyright (c) 2011, Enthought, Inc.
#  All rights reserved.
#------------------------------------------------------------------------------
import itertools
import types

from .byteplay import (
    Code, LOAD_FAST, CALL_FUNCTION, LOAD_GLOBAL, STORE_FAST, LOAD_CONST,
    LOAD_ATTR, STORE_SUBSCR, RETURN_VALUE, POP_TOP,
)
from .factory import EnamlFactory
from .import_hooks import imports


#------------------------------------------------------------------------------
# Compiler Helpers
#------------------------------------------------------------------------------
def _var_name_generator():
    """ Returns a generator that generates sequential variable names for
    use in a code block.

    """
    count = itertools.count()
    while True:
        yield '_var_' + str(count.next())


class EnamlDeclaration(EnamlFactory):
    """ An EnamlFactory which exposes a compiled Enaml declaration
    function with an interface that is easy to use from Python.

    """
    def __init__(self, base, func):
        self.__base__ = base
        self.__func__ = func
        self.__doc__ = func.__doc__
        self.__name__ = func.__name__
        self.__module__ = func.__module__

    def __repr__(self):
        return '%s.%s' % (self.__module__, self.__name__)

    #--------------------------------------------------------------------------
    # Abstract Implementation
    #--------------------------------------------------------------------------
    def __enaml_build__(self, identifiers, toolkit):
        """ An abstractmethod implementation that returns the Enaml
        component generated by the internal compiled Enaml function.

        """
        return self.__func__(identifiers, toolkit)


#------------------------------------------------------------------------------
# Node Visitor
#------------------------------------------------------------------------------
class _NodeVisitor(object):
    """ A node visitor class that is used as base class for the various
    Enaml compilers.

    """
    def visit(self, node):
        """  The main visitor dispatch method.

        """
        name = 'visit_%s' % node.__class__.__name__
        try:
            method = getattr(self, name)
        except AttributeError:
            method = self.default_visit
        method(node)

    def default_visit(self, node):
        """ The default visitor method. Raises an error since there 
        should not be any unhandled nodes.

        """
        raise ValueError('Unhandled Node %s.' % node)


#------------------------------------------------------------------------------
# Declaration Compiler
#------------------------------------------------------------------------------
class DeclarationCompiler(_NodeVisitor):
    """ A visitor which compiles a Declaration node into a code object.

    """
    def __init__(self):
        self.ops = []
        self.name_gen = _var_name_generator()
        self.name_stack = []

    @classmethod
    def compile(cls, node):
        """ Compiles the given Declaration node into a code object.

        Given this sample declaration:
          
            FooWindow(Window) 
                id: foo
                a = '12'
                PushButton:
                    id: btn
                    text = 'clickme'
        
        We generate bytecode that would correspond to a function that 
        looks similar to this:
        
            def FooWindow(identifiers, toolkit):
                f_globals = globals()
                foo_cls = eval('Window', toolkit, f_globals)
                foo = foo_cls.__enaml_call__(identifiers, toolkit)
                identifiers['foo'] = foo
                op = eval('__operator_Equal__', toolkit, f_globals)
                op(foo, 'a', <ast>, <code>, identifiers, f_globals, toolkit)
                btn_cls = eval('PushButton', toolkit, f_globals)
                btn = btn_cls.__enaml_call__(None, toolkit)
                identifiers['btn'] = button
                op = eval('__operator_Equal__', toolkit, f_globals)
                op(item, 'text', <ast>, <code>, identifiers, f_globals, toolkit)
                foo.add_subcomponent(button)
                return foo
        
        """
        compiler = cls()
        compiler.visit(node)
        ops = compiler.ops
        code = Code(ops, [], ['identifiers', 'toolkit'], False, False, True, 
                    node.name, 'Enaml', node.lineno, node.doc)
        return code.to_code()

    def visit_Declaration(self, node):
        """ Creates the bytecode ops for a declaration node. This visitor
        handles creating the component instance and storing it's identifer
        if one is given.

        """
        ops = self.ops
        name_stack = self.name_stack

        name = self.name_gen.next()
        name_stack.append(name)
        ops.extend([
            # f_globals = globals()
            (LOAD_GLOBAL, 'globals'),
            (CALL_FUNCTION, 0x0000),
            (STORE_FAST, 'f_globals'),

            # foo_cls = eval('Window', toolkit, f_globals)
            # foo = foo_cls.__enaml_call__(identifiers, toolkit)
            (LOAD_CONST, eval),
            (LOAD_CONST, node.base.code),
            (LOAD_FAST, 'toolkit'),
            (LOAD_FAST, 'f_globals'),
            (CALL_FUNCTION, 0x0003),
            (LOAD_ATTR, '__enaml_call__'),
            (LOAD_FAST, 'identifiers'),
            (LOAD_FAST, 'toolkit'),
            (CALL_FUNCTION, 0x0002),
            (STORE_FAST, name),
        ])

        if node.identifier:
            ops.extend([
                # identifiers['foo'] = foo
                (LOAD_FAST, name),
                (LOAD_FAST, 'identifiers'),
                (LOAD_CONST, node.identifier),
                (STORE_SUBSCR, None),
            ])

        for item in node.body:
            self.visit(item)
        
        ops.extend([
            # return foo
            (LOAD_FAST, name),
            (RETURN_VALUE, None),
        ])

        name_stack.pop()

    def visit_AttributeDeclaration(self, node):
        """ Creates the bytecode ops for an attribute declaration. This
        visitor handles adding a new attribute to a component.

        """
        ops = self.ops
        name_stack = self.name_stack

        # Load the method that's going to be called and the
        # name of the attribute being declared.
        ops.extend([
            (LOAD_FAST, name_stack[-1]),
            (LOAD_ATTR, 'add_attribute'),
            (LOAD_CONST, node.name),
        ])

        # Generate the ops the load the type (if one was given),
        # and the call the add_attribute method
        type_name = node.type_name
        if type_name is not None:
            op_code = compile(node.type_name, 'Enaml', mode='eval')
            ops.extend([
                (LOAD_CONST, eval),
                (LOAD_CONST, op_code),
                (LOAD_FAST, 'toolkit'),
                (LOAD_FAST, 'f_globals'),
                (CALL_FUNCTION, 0x0003),
                (LOAD_CONST, node.is_event),
                (CALL_FUNCTION, 0x0003),
                (POP_TOP, None),
            ])
        else:
            ops.extend([
                (LOAD_CONST, 'is_event'),
                (LOAD_CONST, node.is_event),
                (CALL_FUNCTION, 0x0101),
                (POP_TOP, None),
            ])

        # Visit the default attribute binding if one exists.
        default = node.default
        if default is not None:
            self.visit(node.default)

    def visit_AttributeBinding(self, node):
        """ Creates the bytecode ops for an attribute binding. This
        visitor handles loading and calling the appropriate operator.

        """
        # XXX handle BoundCodeBlock instead of just BoundExpression
        ops = self.ops
        name_stack = self.name_stack

        # Grab the ast and code object for the expression. These will
        # be passed to the binding operator.
        expr_ast = node.binding.expr.py_ast
        expr_code = node.binding.expr.code
        op_code = compile(node.binding.op, 'Enaml', mode='eval')

        # A binding is accomplished by loading the appropriate binding
        # operator function and passing it the a number of arguments:
        #
        # op = eval('__operator_Equal__', toolkit, f_globals)
        # op(item, 'a', <ast>, <code>, identifiers, f_globals, toolkit)
        ops.extend([
            (LOAD_CONST, eval),
            (LOAD_CONST, op_code),
            (LOAD_FAST, 'toolkit'),
            (LOAD_FAST, 'f_globals'),
            (CALL_FUNCTION, 0x0003),
            (LOAD_FAST, name_stack[-1]),
            (LOAD_CONST, node.name),
            (LOAD_CONST, expr_ast),
            (LOAD_CONST, expr_code),
            (LOAD_FAST, 'identifiers'),
            (LOAD_FAST, 'f_globals'),
            (LOAD_FAST, 'toolkit'),
            (CALL_FUNCTION, 0x0007),
            (POP_TOP, None),
        ])

    def visit_Instantiation(self, node):
        """ Create the bytecode ops for a component instantiation. This 
        visitor handles calling another derived component and storing
        its identifier, if given.
        
        """
        ops = self.ops
        name_stack = self.name_stack

        # This is similar logic to visit_Declaration
        name = self.name_gen.next()
        name_stack.append(name)

        op_code = compile(node.name, 'Enaml', mode='eval')
        ops.extend([
            # btn_cls = eval('PushButton', toolkit, f_globals)
            # btn = btn_cls.__enaml_call__(None, toolkit)
            # When instantiating a Declaration, it is called without
            # identifiers, so that it creates it's own new identifiers
            # scope. This means that derived declarations share ids,
            # but the composed children have an isolated id space.
            (LOAD_CONST, eval),
            (LOAD_CONST, op_code),
            (LOAD_FAST, 'toolkit'),
            (LOAD_FAST, 'f_globals'),
            (CALL_FUNCTION, 0x0003),
            (LOAD_ATTR, '__enaml_call__'),
            (LOAD_CONST, None),
            (LOAD_FAST, 'toolkit'),
            (CALL_FUNCTION, 0x0002),
            (STORE_FAST, name),
        ])
        
        if node.identifier:
            ops.extend([
                (LOAD_FAST, name),
                (LOAD_FAST, 'identifiers'),
                (LOAD_CONST, node.identifier),
                (STORE_SUBSCR, None),
            ])

        for item in node.body:
            self.visit(item)
        
        name_stack.pop()
        ops.extend([
            # foo.add_subcomponent(button)
            (LOAD_FAST, name_stack[-1]),
            (LOAD_ATTR, 'add_subcomponent'),
            (LOAD_FAST, name),
            (CALL_FUNCTION, 0x0001),
            (POP_TOP, None),
        ])


#------------------------------------------------------------------------------
# Enaml Compiler
#------------------------------------------------------------------------------
class EnamlCompiler(_NodeVisitor):
    """ A compiler that will compile an enaml module ast node.
    
    The entry point is the `compile` classmethod which will compile
    the ast into an appropriate python object and place the results 
    in the provided module dictionary.

    """
    @classmethod
    def compile(cls, module_ast, module_dict):
        """ The main entry point of the compiler.

        Parameters
        ----------
        module_ast : Instance(enaml_ast.Module)
            The enaml module ast node that should be compiled.
        
        module_dict : dict
            The dictionary of the Python module into which we are
            compiling the enaml code.
        
        """
        compiler = cls(module_dict)
        compiler.visit(module_ast)

    def __init__(self, module_dict):
        """ Initialize a compiler instance.

        Parameters
        ----------
        module_dict : dict
            The module dictionary into which the compiled objects are 
            placed.
        
        """
        # This ensures that the key '__builtins__' exists in the mod dict.
        exec '' in module_dict
        self.global_ns = module_dict

    def visit_Module(self, node):
        """ The module node visitory method. Used internally by the
        compiler.

        """
        if node.doc:
            self.global_ns['__doc__'] = node.doc
        for item in node.body:
            self.visit(item)
    
    def visit_Python(self, node):
        """ A visitor which adds a chunk of raw Python into the module.

        """
        try:
            exec node.code in self.global_ns
        except Exception as e:
            msg = ('Unable to evaluate raw Python code on lineno %s. '
                   'Original exception was %s.')
            exc_type = type(e)
            raise exc_type(msg % (node.lineno, e))
        
    def visit_Import(self, node):
        """ The import statement visitor method. This ensures that imports
        are performed with the enaml import hook in-place.

        """
        with imports():
            try:
                exec node.code in self.global_ns
            except Exception as e:
                msg = ('Unable to evaluate import on lineno %s. '
                       'Original exception was %s.')
                exc_type = type(e)
                raise exc_type(msg % (node.lineno, e))

    def visit_Declaration(self, node):
        """ The declaration node visitor. This will add an instance
        of EnamlDeclaration to the module.

        """
        func_code = DeclarationCompiler.compile(node)
        func = types.FunctionType(func_code, self.global_ns)
        wrapper = EnamlDeclaration(node.base.py_txt.strip(), func)
        self.global_ns[node.name] = wrapper

