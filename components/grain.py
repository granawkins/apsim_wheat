from components import BaseComponent
from utils import interpolate

class Grain(BaseComponent):

    def __init__(self, plant, parent=None):
        super().__init__(plant, parent)
        self.biomass_total = self.plant.vars['meal_dm_init']
        self.n_grains = None
        self.demand_cache = {}

    def partition(self, available_biomass):
        self.biomass_total += available_biomass
        self.log('biomass_grain', available_biomass)
        self.log('biomass_total', self.biomass())

        unfulfilled = self.demand() - available_biomass
        self.unfulfilled_total = unfulfilled
        self.log('unfulfilled_grain', unfulfilled)

    def demand(self, env_conditions=None):
        # Only calculate during flowering
        if 'postflowering' not in self.plant.phase_composite_phases:
            return 0

        if not env_conditions:
            if self.plant.age in self.demand_cache:
                return self.demand_cache[self.plant.age]
            else:
                raise Exception("Missing env_conditions to calculate grain demand")

        # Determine number of grains at anthesis
        if not self.n_grains:
            stem_weight = self.plant.components['stem'].biomass()
            grains_per_gram_stem = self.plant.vars['grain_per_gram_stem']
            self.n_grains = stem_weight * grains_per_gram_stem

        # Determine fill rate based on growth phase
        if self.plant.phase_name == 'flowering':
            fill_rate = self.plant.vars['potential_grain_growth_rate']
        elif self.plant.phase_name == 'start_of_grain_filling':
            fill_rate = self.plant.vars['potential_grain_filling_rate']

        # Growth modified by temperature factor
        temperature_factor = interpolate(self.plant.vars['x_temp_grainfill'],
                                         self.plant.vars['y_rel_grainfill'],
                                         env_conditions['air_temp_mean'])

        # Determine nitrogen factor
        potential_rate = self.plant.vars['potential_grain_n_filling_rate']
        minimum_rate = self.plant.vars['minimum_grain_n_filling_rate']
        deficit_multiplier = self.plant.vars['n_fact_grain']

        stem_nitrogen_factor = self.plant.components['stem'].nitrogen_factor()
        leaf_nitrogen_factor = self.plant.components['leaf'].nitrogen_factor()

        nitrogen_factor = (potential_rate / minimum_rate) * deficit_multiplier * \
                          (stem_nitrogen_factor + leaf_nitrogen_factor)

        grain_demand = self.n_grains * fill_rate * temperature_factor * nitrogen_factor
        max_grain_size = self.plant.vars['max_grain_size']
        max_demand = max_grain_size * self.n_grains - self.biomass_total
        grain_demand = min(grain_demand, max_demand)

        self.log('grain_demand', grain_demand)
        self.demand_cache[self.plant.age] = grain_demand
        return min(grain_demand, max_demand)

    def retranslocate_to(self, amount):
        self.biomass_total += amount
        self.log('biomass_grain_retranslocated_to', amount)
