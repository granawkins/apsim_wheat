from components import BaseComponent, Grain, Pod
from utils import interpolate

class Head(BaseComponent):

    def __init__(self, plant, parent=None):
        super().__init__(plant, parent)
        self.components['grain'] = Grain(plant, self)
        self.components['pod'] = Pod(plant, self)

    def partition(self, available_biomass, env_conditions, total_daily_accumulation):
        grain = self.components['grain']
        pod = self.components['pod']

        demand_grain = grain.demand(env_conditions=env_conditions)
        demand_pod = pod.demand(total_daily_accumulation)
        demand_head = demand_grain + demand_pod
        biomass_head = min(demand_head, available_biomass)
        self.log('biomass_head', biomass_head)
        self.log('biomass_total', self.biomass())
        if biomass_head == 0:
            return 0

        biomass_grain = (demand_grain / demand_head) * biomass_head
        grain.partition(biomass_grain)

        biomass_pod = (demand_pod / demand_head) * biomass_head
        pod.partition(biomass_pod)

        return available_biomass - biomass_head

    def retranslocate_from(self, target):
        return self.components['pod'].retranslocate_from(target)

    def retranslocate_to(self, amount):
        unfulfilled_total = self.unfulfilled()
        for component in self.components.values():
            retranslocated = amount * (component.unfulfilled() / unfulfilled_total)
            component.retranslocate_to(retranslocated)
