
import array
import json
import random

import numpy
import scipy

from deap import algorithms, base, creator, tools
from data import MenuDB, HealthProfile
from lib import tee


with open('./db.json') as f:
    db = MenuDB(f)

with open('./menu.json') as f:
    menu = json.load(f)

# P = HealthProfile(weight=295, body_fat_percent=43)
P = HealthProfile(weight=290, body_fat_percent=42.5, calorie_adjustment=-100)

selections = menu['selections']
selection_keys = list(selections.keys())
num_selections = len(selections)

# NGEN = 100
# MU = 10000
NGEN = 100
MU = 5000
LAMBDA = 100
CXPB = 0.7
MUTPB = 0.2

# creator.create("Fitness", base.Fitness,
#         weights=(-1.0, -1.0, -1000000*float(num_selections)))
creator.create("Fitness", base.Fitness, weights=(-1.0,))
creator.create("Individual", array.array, typecode="d", fitness=creator.Fitness)

def random_individual():
    result = [(0 if random.random() < 0.5 else random.uniform(0, 10))
              for i in range(num_selections)]

    for i, x in enumerate(result):
        if random.random() < float(3)/MU:
            result[i] = x*random.uniform(5, 10)

    return creator.Individual(result)

toolbox = base.Toolbox()
# toolbox.register("attr", random.uniform, 0, 200)
# toolbox.register(
#         "individual", tools.initRepeat, creator.Individual, toolbox.attr,
#         n=num_selections)
toolbox.register("population", tools.initRepeat, list, random_individual)

def evaluate(individual):
    k, c, g, p, s, f = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    neg_penalty = 0.0
    non_int_penalty = 0.0
    min_nz_penalty = 0
    selection_penalty = 0
    num_items = 0
    num_attrs = len(individual)

    for i, servings in enumerate(individual):
        non_int_penalty += 0.5*(1 - numpy.cos(2*numpy.pi*servings))
        servings = int(round(servings))

        if servings < 0:
            neg_penalty -= servings

        if servings < 0:
            servings = 0

        if servings > 0:
            num_items += 1

        key = selection_keys[i]
        selection_entry = selections[key] or {}
        entry = db[key]

        mn = selection_entry.get('min')
        if mn is not None and servings < mn:
            selection_penalty += mn - servings

        mx = selection_entry.get('max')
        if mx is not None and mx < servings:
            selection_penalty += servings - mx

        if servings > 0 and servings < entry.min_nz_count:
            min_nz_penalty += (entry.min_nz_count - servings)

        factor = entry.increment*servings

        k += factor*entry.calories
        c += factor*entry.carbs
        g += factor*entry.fat
        p += factor*entry.protein
        s += factor*entry.sodium
        f += factor*entry.fiber

    k0, c0, g0, p0, s0, f0 = (
        P.adjusted_calorie_target,
        P.carbs_target,
        P.fat_target,
        P.protein_target,
        P.sodium_target,
        P.fiber_target)

    k1 = 1.0*k0
    c1 = 1.1*c0
    g1 = 1.05*g0
    p1 = 1.1*p0
    s1 = 1.2*s0
    f1 = 1.4*f0

    # k1, c1, g1, p1, s1, f1 = tuple(
        # round(10.1*x) for x in (k0, c0, g0, p0, s0, f0))

    rktd = -min((k-k0)/k0, 0)
    rctd = -min((c-c0)/c0, 0)
    rgtd = -min((g-g0)/g0, 0)
    rptd = -min((p-p0)/p0, 0)
    rstd = -min((s-s0)/s0, 0)
    rftd = -min((f-f0)/f0, 0)

    rkld = max((k-k1)/k1,0)
    rcld = max((c-c1)/c1,0)
    rgld = max((g-g1)/g1,0)
    rpld = max((p-p1)/p1,0)
    rsld = max((s-s1)/s1,0)
    rfld = max((f-f1)/f1,0)

    wrds = (rktd + 4.0*rkld +
            rctd + 4.0*rcld +
            rgtd + 4.0*rgld +
            4.0*(rptd + 4.0*rpld) +
            rstd + 4.0*rsld +
            rftd + 4.0*rfld)

    non_int_penalty /= num_attrs
    neg_penalty /= num_attrs

    menu_constraint_penalty = 0
    menu_constraints = menu.get('size', {})
    mn = menu_constraints.get('min')
    if mn is not None and num_items < mn:
        menu_constraint_penalty += mn - num_items
    mx = menu_constraints.get('min')
    if mx is not None and mx < num_items:
        menu_constraint_penalty += num_items - mx

    penalty = (neg_penalty +
               non_int_penalty +
               min_nz_penalty +
               selection_penalty +
               menu_constraint_penalty)

    return ((wrds + penalty)*numpy.exp(penalty),)
    # return (neg_penalty, non_int_penalty, wrds)

toolbox.register("evaluate", evaluate)
toolbox.register("mate", tools.cxTwoPoint)
toolbox.register("mutate", tools.mutFlipBit, indpb=0.05)
# toolbox.register("select", tools.selNSGA2)
toolbox.register("select", tools.selTournament, tournsize=3)

pop = toolbox.population(n=MU)
# hof = tools.ParetoFront()
hof = tools.HallOfFame(1)
stats = tools.Statistics(lambda ind: ind.fitness.values)
stats.register("avg", numpy.mean, axis=0)
stats.register("std", numpy.std, axis=0)
stats.register("min", numpy.min, axis=0)
stats.register("max", numpy.max, axis=0)

# algorithms.eaMuPlusLambda(
#     pop, toolbox, MU, LAMBDA, CXPB, MUTPB, NGEN, stats, halloffame=hof)
pop, log = algorithms.eaSimple(
    pop, toolbox, cxpb=CXPB, mutpb=MUTPB, ngen=NGEN, stats=stats,
    halloffame=hof, verbose=True)

from pprint import pprint
pprint(stats.compile(pop))
pprint(stats.compile(hof))
pprint(hof)


print('\n\n\n')

def display_individual(ind):
    k, c, g, p, s, f = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    for i, servings in enumerate(ind):
        servings = int(round(servings))
        if servings == 0:
            continue

        key = selection_keys[i]
        entry = db[key]

        factor = entry.increment*servings

        desc = ' '.join((entry.unit, entry.description))
        print('(%2d) %5.1f %-30s' % (
            servings,
            factor*entry.unit_count,
            desc[:min(len(desc),30)]),
            end=' ')

        print('K %6.1f C %6.1f G %6.1f P %6.1f S %6.1f F %6.1f' % (
            factor*entry.calories,
            factor*entry.carbs,
            factor*entry.fat,
            factor*entry.protein,
            factor*entry.sodium,
            factor*entry.fiber))

        k += factor*entry.calories
        c += factor*entry.carbs
        g += factor*entry.fat
        p += factor*entry.protein
        s += factor*entry.sodium
        f += factor*entry.fiber

    print('')
    print('%-41s' % 'TOTAL', end=' ')
    print('K %6.1f C %6.1f G %6.1f P %6.1f S %6.1f F %6.1f' % (
        k, c, g, p, s, f))

    print('%-41s' % 'TARGETS', end=' ')
    print('K %6.1f C %6.1f G %6.1f P %6.1f S %6.1f F %6.1f' % (
        P.adjusted_calorie_target,
        P.carbs_target,
        P.fat_target,
        P.protein_target,
        P.sodium_target,
        P.fiber_target
    ))

    print('')
    print('FITNESS {}'.format(
        ', '.join(str(x) for x in ind.fitness.getValues())))
    print('')

with open('plans.txt', 'a') as f:
    with tee(f):
        display_individual(hof[0])

