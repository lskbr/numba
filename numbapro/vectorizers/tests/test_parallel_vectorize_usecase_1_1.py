
import unittest
import numpy as np
from llvm_cbuilder import shortnames as C
from llvm_cbuilder import CExecutor, CDefinition
from llvm.core import Module
from llvm.ee import EngineBuilder
from numbapro.vectorizers._common import _llvm_ty_to_dtype
from numbapro.vectorizers.parallel import parallel_vectorize_from_func
from .support import addtest, main


class OneOne(CDefinition):
    def body(self, inval):
        self.ret( (inval * inval).cast(self.OUT_TYPE) )

    def specialize(cls, itype, otype):
        cls._name_ = '.'.join(map(str, ['oneone', itype, otype]))
        cls._retty_ = otype
        cls._argtys_ = [
            ('inval', itype),
        ]
        cls.OUT_TYPE = otype

@addtest
class TestParallelVectorize(unittest.TestCase):
    def test_parallelvectorize_d_d(self):
        self.template(C.double, C.double)

    def test_parallelvectorize_d_f(self):
        self.template(C.double, C.float)

    def test_parallelvectorize_generic(self):
        module = Module.new(__name__)

        eb = EngineBuilder.new(module).mattrs('-avx').create()
        exe = CExecutor(eb)

        tyslist = [
            (C.double, C.double),
            (C.float,  C.float),
            (C.int64,  C.int64),
            (C.int32,  C.int32),
        ]

        tynumslist = []
        for tys in tyslist:
            tynumslist.append(list(map(_llvm_ty_to_dtype, tys)))

        oneone_defs = [OneOne(*tys)(module) for tys in tyslist]

        ufunc = parallel_vectorize_from_func(oneone_defs, tynumslist, exe.engine)
        #print(module)
        module.verify()

        self.check(ufunc, np.double)
        self.check(ufunc, np.float32)
        self.check(ufunc, np.int64)
        self.check(ufunc, np.int32)

    def check(self, ufunc, ty):
        x = np.linspace(0., 10., 1000).astype(ty)

        ans = ufunc(x)
        gold = x * x

        for x, y in zip(ans, gold):
            if y != 0:
                err = abs(x - y)/y
                self.assertTrue(err < 1e-6)
            else:
                self.assertEqual(x, y)


    def template(self, itype, otype):
        module = Module.new(__name__)
        eb = EngineBuilder.new(module).mattrs('-avx').create()
        exe = CExecutor(eb)

        def_oneone = OneOne(itype, otype)
        oneone = def_oneone(module)

        tyslist = [list(map(_llvm_ty_to_dtype, [itype, otype]))]
        ufunc = parallel_vectorize_from_func(oneone, tyslist, exe.engine)
        # print(module)
        module.verify()

        self.check(ufunc, np.double)


if __name__ == '__main__':
    main()

