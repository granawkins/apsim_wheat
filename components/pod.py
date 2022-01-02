from components.base_component import BaseComponent
from utils import interpolate

class Pod(BaseComponent):

    def __init__(self, plant, parent=None):
        super().__init__(plant, parent)
        self.demand_cache = {}

        initial_biomass = self.plant.vars['pod_dm_init']
        self.structural_fraction = 0
        self.biomass_structural = initial_biomass * self.structural_fraction
        self.biomass_non_structural = initial_biomass * (1 - self.structural_fraction)
        self.biomass_total = self.biomass_structural + self.biomass_non_structural

    def partition(self, available_biomass):
        biomass_structural = available_biomass * self.structural_fraction
        self.biomass_structural += biomass_structural
        self.biomass_total += biomass_structural
        self.log('biomass_pod_structural', biomass_structural)

        biomass_non_structural = available_biomass * (1 - self.structural_fraction)
        self.biomass_non_structural += biomass_non_structural
        self.biomass_total += biomass_non_structural
        self.log('biomass_pod_non_structural', biomass_non_structural)
        self.log('biomass_total', self.biomass())

        unfulfilled = self.demand() - available_biomass
        self.unfulfilled_total = unfulfilled
        self.log('unfulfilled_pod', unfulfilled)

    def demand(self, total_daily_accumulation=None):
        if not total_daily_accumulation:
            if self.plant.age in self.demand_cache:
                return self.demand_cache[self.plant.age]
            else:
                raise Exception("Missing total_daily_accumulation to calculate pod demand")

        pod_demand_fraction = interpolate(self.plant.phase_modifiers['x_stage_no_partition'],
                                         self.plant.phase_modifiers['y_frac_pod'],
                                         self.plant.stage)
        grain_demand = self.parent.components['grain'].demand()
        if grain_demand > 0:
            pod_demand = grain_demand * pod_demand_fraction
        else:
            pod_demand = total_daily_accumulation * pod_demand_fraction

        self.demand_cache[self.plant.age] = pod_demand
        return pod_demand

    def retranslocate_from(self, target):
        actual = min(target, self.biomass_non_structural)
        self.biomass_non_structural -= actual
        self.biomass_total -= actual
        self.log('biomass_pod_retranslocated_from', actual)
        return actual

    def retranslocate_to(self, amount):
        self.biomass_non_structural += amount
        self.biomass_total += amount
        self.log('biomass_pod_retranslocated_to', amount)
