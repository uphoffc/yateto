#!/usr/bin/env python3

from yateto import Generator, Tensor
from yateto.generator import simpleParameterSpace
from yateto.input import parseXMLMatrixFile
from yateto.ast.visitor import PrettyPrinter, PrintEquivalentSparsityPatterns
from yateto.ast.transformer import DeduceIndices, EquivalentSparsityPattern, StrengthReduction, FindContractions, ImplementContractions, FindIndexPermutations, SelectIndexPermutations
from yateto.ast.node import Add
import itertools

maxDegree = 5
order = maxDegree+1
numberOf2DBasisFunctions = order*(order+1)//2
numberOf3DBasisFunctions = order*(order+1)*(order+2)//6
numberOfQuantities = 9
multipleSims = True
#~ multipleSims = False

if multipleSims:
  qShape = (8, numberOf3DBasisFunctions, numberOfQuantities)
  qi = lambda x: 's' + x
else:
  qShape = (numberOf3DBasisFunctions, numberOfQuantities)
  qi = lambda x: x

clones = {
  'star': ['star[0]', 'star[1]', 'star[2]'],
}
db = parseXMLMatrixFile('matrices_{}.xml'.format(numberOf3DBasisFunctions), clones)

# Quantities
Q = Tensor('Q', qShape)
I = Tensor('I', qShape)
D = [Q]

# Flux solver
AplusT = [Tensor('AplusT[{}]'.format(dim), (numberOfQuantities, numberOfQuantities)) for dim in range(4)]
AminusT = [Tensor('AminusT[{}]'.format(dim), (numberOfQuantities, numberOfQuantities)) for dim in range(4)]

g = Generator()

volumeSum = Q[qi('kp')]
for i in range(3):
  volumeSum += db.kDivM[i]['kl'] * I[qi('lq')] * db.star[i]['qp']
volume = (Q[qi('kp')] <= volumeSum)
g.add('volume', volume)

localFluxSum = Q[qi('kp')]
for i in range(4):
  localFluxSum += db.rDivM[i]['km'] * db.fMrT[i]['ml'] * I[qi('lq')] * AplusT[i]['qp']
localFlux = (Q[qi('kp')] <= localFluxSum)
g.add('localFlux', localFlux)

neighbourFlux = lambda i,j,h: Q[qi('kp')] <= Q[qi('kp')] + db.rDivM[i]['km'] * db.fP[h]['mn'] * db.rT[j]['nl'] * I[qi('lq')] * AminusT[i]['qp']
g.addFamily('neighboringFlux', simpleParameterSpace(4,4,3), neighbourFlux)

for i in range(maxDegree):
  derivativeSum = Add()
  for j in range(3):
    derivativeSum += db.kDivMT[j]['kl'] * D[i][qi('lq')] * db.star[j]['qp']
  derivativeSum = DeduceIndices( Q[qi('kp')].indices ).visit(derivativeSum)
  derivativeSum = EquivalentSparsityPattern().visit(derivativeSum)
  D.append( Tensor('dQ[{0}]'.format(i+1), qShape, spp=derivativeSum.eqspp()) )
  derivative = D[i+1][qi('kp')] <= derivativeSum

  g.add('derivative[{}]'.format(i), derivative)
  
  #~ derivative = DeduceIndices().visit(derivative)
  #~ derivative = EquivalentSparsityPattern().visit(derivative)
  #~ PrintEquivalentSparsityPatterns('sparsityPatterns/derivative{}/'.format(i)).visit(derivative)

g.generate('test')

#~ PrintEquivalentSparsityPatterns('sparsityPatterns/volume/').visit(volume)
#~ PrintEquivalentSparsityPatterns('sparsityPatterns/localFlux/').visit(localFlux)

#~ nDof = 6
#~ nVar = 40
#~ A = Tensor('A', (nVar, nDof, nDof, nDof))
#~ B = Tensor('B', (nVar, nDof, nDof, nDof))
#~ C1 = Tensor('C1', (nDof, nDof))
#~ C2 = Tensor('C2', (nDof, nDof))
#~ C3 = Tensor('C3', (nDof, nDof))
#~ test = A['nxyz'] <= B['nijk'] * C1['ix'] * C2['jy'] * C3['kz']

#~ test = neighbourFlux(0,0,0)
#~ test = Tensor('D', (24,24,24,24,24))['abckl'] <= Tensor('A', (24,24,24,24))['ijmc'] * Tensor('B', (24,24,24,24))['mkab'] * Tensor('C', (24,24,24))['ijl']
#~ test = Tensor('D', (24,24,4,4,4))['abckl'] <= Tensor('A', (24,24,4,4))['ijmc'] * Tensor('B', (4,4,24,24))['mkab'] * Tensor('C', (24,24,4))['ijl']
#~ test = Tensor('D', (4,4,4,4,4,4))['abcijk'] <= Tensor('A', (4,4,4,4))['ijmc'] * Tensor('B', (4,4,4,4))['mkab']

#~ test = Tensor('D', (4,4,4))['mij'] <= Tensor('A', (4,4))['ik'] * Tensor('B', (4,4))['kj'] * Tensor('C', (4,4))['ms']
test = Tensor('D', (4,4,4,4))['hmyj'] <= Tensor('F', (4,4,4))['hiy'] * Tensor('A', (4,4))['ki'] * Tensor('B', (4,4,4))['zkj'] * Tensor('C', (4,4))['ms']
#~ test = volume
PrettyPrinter().visit(test)

test = DeduceIndices().visit(test)
PrettyPrinter().visit(test)

test = EquivalentSparsityPattern().visit(test)
PrettyPrinter().visit(test)

test = StrengthReduction().visit(test)
PrettyPrinter().visit(test)

test = FindContractions().visit(test)
PrettyPrinter().visit(test)

test = FindIndexPermutations().visit(test)
test = SelectIndexPermutations().visit(test)
PrettyPrinter().visit(test)

test = ImplementContractions().visit(test)
PrettyPrinter().visit(test)
