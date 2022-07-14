
import collections.abc
import functools
import json
import weakref

functools.lru_cache

functools.cached_property

class MenuEntry:
    def __init__(self, parent, key):
        self.parent = weakref.proxy(parent)
        self.key = key

    @functools.cached_property
    def obj(self):
        return self.parent._data.get(self.key) or {}

    @functools.cached_property
    def description(self):
        return self.obj.get('desc') or self.key

    @functools.cached_property
    def increment(self):
        return self.obj.get('inc') or 1.0

    @functools.cached_property
    def unit_count(self):
        count = self.obj.get('count') or 1
        if isinstance(count, list):
            count = count[1] if len(count) > 1 else 1
        return count

    @functools.cached_property
    def min_nz_count(self):
        count = self.obj.get('count') or 1
        if isinstance(count, list):
            count = count[0] if len(count) > 0 else 1
        return count

    @functools.cached_property
    def unit(self):
        return self.obj.get('unit') or 'unit'

    @functools.cached_property
    def nut_block(self):
        try:
            ingredients = self.obj['ingredients']
        except KeyError:
            return self.obj

        result = {}
        attrs = 'kcgpsf'
        factor = 1.0

        for x in ingredients:
            if isinstance(x, str):
                parent_obj = self.parent.get(x).nut_block
                for a in attrs:
                    result[a] = (
                        result.get(a, 0) + round(factor*parent_obj.get(a, 0)))
                factor = 1.0
            else:
                factor = x

        return result

    @functools.cached_property
    def calories(self):
        return self.nut_block.get('k', 0)

    @functools.cached_property
    def carbs(self):
        return self.nut_block.get('c', 0)

    @functools.cached_property
    def fat(self):
        return self.nut_block.get('g', 0)

    @functools.cached_property
    def protein(self):
        return self.nut_block.get('p', 0)

    @functools.cached_property
    def sodium(self):
        return self.nut_block.get('s', 0)

    @functools.cached_property
    def fiber(self):
        return self.nut_block.get('f', 0)


class MenuDB(collections.abc.Mapping, collections.abc.Hashable):
    def __init__(self, f):
        self._data = json.load(f)

    def __hash__(self):
        return id(self)

    @functools.lru_cache
    def __getitem__(self, key):
        return MenuEntry(self, key)

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)


class HealthProfile:
    def __init__(self, weight, body_fat_percent, protein_factor=1.0,
                 calories_per_g_fat=9.0, calories_per_g_protein=4.0,
                 calories_per_g_carbs=4.0, fat_percent=30, protein_percent=30,
                 sodium_target=3000, fiber_target=35, calorie_adjustment=0):
        self.weight = weight
        self.body_fat_percent = body_fat_percent
        self.protein_factor = protein_factor
        self.calories_per_g_fat = calories_per_g_fat
        self.calories_per_g_protein = calories_per_g_protein
        self.calories_per_g_carbs = calories_per_g_carbs
        self.fat_percent = fat_percent
        self.protein_percent = protein_percent
        self.sodium_target = sodium_target
        self.fiber_target = fiber_target
        self.calorie_adjustment = calorie_adjustment

    @property
    def lean_weight(self):
        return round(self.weight*(100.0 - self.body_fat_percent)/100)

    @property
    def carbs_percent(self):
        return 100.0 - self.fat_percent - self.protein_percent

    @property
    def calorie_target(self):
        return round(100.0*self.protein_calorie_target/self.protein_percent)

    @property
    def adjusted_calorie_target(self):
        return round(self.calorie_target + self.calorie_adjustment)

    @property
    def protein_calorie_target(self):
        return round(self.protein_target*self.calories_per_g_protein)

    @property
    def fat_calorie_target(self):
        return round(self.calorie_target*self.fat_percent/100.0)

    @property
    def carbs_calorie_target(self):
        return (self.calorie_target -
                self.fat_calorie_target -
                self.protein_calorie_target)

    @property
    def fat_target(self):
        return round(self.fat_calorie_target/self.calories_per_g_fat)

    @property
    def protein_target(self):
        return round(self.protein_factor*self.lean_weight)

    @property
    def carbs_target(self):
        return round(self.carbs_calorie_target/self.calories_per_g_carbs)

