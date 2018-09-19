import subprocess
from ..cache import RoutineGenerator

LIBXSMM_GENERATOR = 'libxsmm_gemm_generator'

class Libxsmm(object):
  def __init__(self, arch, descr):
    self._arch = arch
    self._descr = descr
  
  def generateRoutineName(self, gemm):
    alpha = '1' if gemm['alpha'] == 1 else '_1'
    return 'libxsmm_m{M}_n{N}_k{K}_ldA{LDA}_ldB{LDB}_ldC{LDC}_alpha{alphaSubs}_beta{beta}_alignedA{alignedA}_alignedC{alignedC}_{prefetch}'.format(alphaSubs=alpha, **gemm)
  
  def _pointer(self, term, offset2):
    o = term.memoryLayout.address(offset2)
    if o > 0:
      return '{} + {}'.format(term.name, o)
    return term.name
    
  def generate(self, cpp, routineCache):
    d = self._descr
    m, n, k = d.mnk()
    ldA = d.leftTerm.memoryLayout.stridei(1)
    ldB = d.rightTerm.memoryLayout.stridei(1)
    ldC = d.result.memoryLayout.stridei(1)
    
    assert (m,k) in d.leftTerm.memoryLayout
    assert (k,n) in d.rightTerm.memoryLayout
    assert (m,n) in d.result.memoryLayout
    
    gemm = {
      'M':            m.size(),
      'N':            n.size(),
      'K':            k.size(),
      'LDA':          ldA,
      'LDB':          ldB,
      'LDC':          ldC,
      'alpha':        int(d.alpha),
      'beta':         int(d.beta),
      'alignedA':     int(d.alignedA),
      'alignedC':     int(d.alignedC),
      'prefetch':     'pfsigonly'
    }
    
    routineName = self.generateRoutineName(gemm)
    
    cpp( '{}({}, {}, {}, nullptr, nullptr, nullptr);'.format(
      routineName,
      self._pointer(d.leftTerm, (m.start, k.start)),
      self._pointer(d.rightTerm, (k.start, n.start)),
      self._pointer(d.result, (m.start, n.start))
    ))
    
    routineCache.addRoutine(routineName, ExecuteLibxsmm(self._arch, gemm))
    
    return 2 * m.size() * n.size() * k.size()

class ExecuteLibxsmm(RoutineGenerator):  
  def __init__(self, arch, gemmDescr):
    self._arch = arch
    self._gemmDescr = gemmDescr
  
  def __eq__(self, other):
    return self._arch == other._arch and self._gemmDescr == other._gemmDescr
  
  def header(self, cpp):
    with cpp.PPIfndef('NDEBUG'):
      cpp('extern long long libxsmm_num_total_flops;')
    with cpp.PPIf('defined( __SSE3__) || defined(__MIC__)'):
      cpp.includeSys('immintrin.h')
  
  def __call__(self, routineName, fileName):
    argList = [
      LIBXSMM_GENERATOR,
      'dense',
      fileName,
      routineName,
      self._gemmDescr['M'],
      self._gemmDescr['N'],
      self._gemmDescr['K'],
      self._gemmDescr['LDA'],
      self._gemmDescr['LDB'],
      self._gemmDescr['LDC'],
      self._gemmDescr['alpha'],
      self._gemmDescr['beta'],
      self._gemmDescr['alignedA'],
      self._gemmDescr['alignedC'],
      self._arch.name,
      self._gemmDescr['prefetch'],
      self._arch.precision + 'P'
    ]

    try:
      subprocess.call([str(arg) for arg in argList])
    except OSError:
      raise RuntimeError('Libxsmm executable "{}" not found. (Make sure to add the folder containing the executable to your PATH.)'.format(LIBXSMM_GENERATOR))
    
    return 'void {name}(const {type}* A, const {type}* B, {type}* C, const {type}* A_prefetch, const {type}* B_prefetch, const {type}* C_prefetch);'.format(name=routineName, type=self._arch.typename)
  
