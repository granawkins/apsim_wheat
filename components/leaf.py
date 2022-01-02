from components.base_component import BaseComponent
from utils import interpolate

class Leaf(BaseComponent):

    def __init__(self, plant, parent=None):
        super().__init__(plant, parent)
        self.biomass_total = self.plant.vars['leaf_dm_init']
        self.n_leaves = self.plant.vars['leaf_no_at_emerg']
        self.n_nodes = self.n_leaves
        self.lai = self.plant.vars['initial_tpla']
        self.biomass_senescence = 0
        self.leaf_senescence = 0
        self.lai_senescence = 0

    def partition(self, available_biomass, step_tt):
        # Biomass
        leaf_fraction = interpolate(self.plant.phase_modifiers['x_stage_no_partition'],
                                    self.plant.phase_modifiers['y_frac_leaf'],
                                    self.plant.stage)
        biomass_leaf = available_biomass * leaf_fraction
        self.biomass_total += biomass_leaf
        self.log('biomass_leaf', biomass_leaf)
        self.log('biomass_total', self.biomass())

        self.growth(biomass_leaf, step_tt)
        if 'leaf_senescence' in self.plant.phase_composite_phases and self.plant.stage > 3.4:
            self.senescence(biomass_leaf, step_tt)

        return available_biomass - biomass_leaf

    def nitrogen_factor(self):
        nitrogen_concentration = 0.0001
        nitrogen_critical = interpolate(self.plant.phase_modifiers['x_stage_code'],
                                        self.plant.phase_modifiers['y_n_conc_crit_leaf'],
                                        self.plant.stage)
        nitrogen_minimum = interpolate(self.plant.phase_modifiers['x_stage_code'],
                                       self.plant.phase_modifiers['y_n_conc_min_leaf'],
                                       self.plant.stage)
        co2_factor = 1
        nitrogen_factor = (nitrogen_concentration - nitrogen_minimum) / ((nitrogen_critical * co2_factor) - nitrogen_minimum)
        self.log('leaf_nitrogen_factor', nitrogen_factor)
        return nitrogen_factor

    def growth(self, biomass_leaf, step_tt):
        # Stress factors for canopy expansion
        nitrogen_sce = 1
        phosphorus_sce = 1
        water_sce = 1

        # Node formation potential
        potential_node_formation_rate = interpolate(self.plant.vars['x_node_no_app'],
                                                    self.plant.vars['y_node_app_rate'],
                                                    self.n_nodes)
        potential_node_increase = step_tt / potential_node_formation_rate
        self.log('potential_node_increase', potential_node_increase)
        self.n_nodes += potential_node_increase #TODO: Verify, this is a guess

        # Leaf formation potential
        leaf_potential = lambda n: interpolate(self.plant.vars['x_node_no_leaf'],
                                              self.plant.vars['y_leaves_per_node'],
                                              n)
        environmental_stress_canopy_expansion = min(min(nitrogen_sce, phosphorus_sce)**2, water_sce)
        leaf_number = min(self.n_nodes, leaf_potential(self.n_nodes)) + \
                      (leaf_potential(self.n_nodes + potential_node_increase) - leaf_potential(self.n_nodes)) * \
                      environmental_stress_canopy_expansion
        potential_leaf_increase = leaf_number * potential_node_increase
        self.log('potential_leaf_increase', potential_leaf_increase)

        # Leaf area index
        plant_population = 1
        growing_leaf_number = self.plant.vars['node_no_correction']
        current_and_growing_leaves = self.n_leaves + growing_leaf_number
        potential_node_leaf_area = interpolate(self.plant.vars['x_node_no'],
                                               self.plant.vars['y_leaf_size'],
                                               current_and_growing_leaves)
        self.log('potential_node_leaf_area', potential_node_leaf_area)
        potential_leaf_area_increase = potential_leaf_increase * plant_population * potential_node_leaf_area

        lai_increase_stressed = potential_leaf_area_increase * min(nitrogen_sce, phosphorus_sce, water_sce)
        lai_increase_carbon_limited = biomass_leaf * interpolate(self.plant.vars['x_lai'],
                                                                 self.plant.vars['y_sla_max'],
                                                                 self.lai)
        lai_increase = min(lai_increase_stressed, lai_increase_carbon_limited)
        self.log('lai_increase', lai_increase)
        self.lai += lai_increase

        # Leaf formation actual
        lai_stressed_factor = lai_increase / lai_increase_stressed
        lai_increase_factor = interpolate(self.plant.vars['x_lai_ratio'],
                                          self.plant.vars['y_leaf_no_fraction'],
                                          lai_stressed_factor)
        actual_leaf_increase = potential_leaf_increase * lai_increase_factor
        self.log('actual_leaf_increase', actual_leaf_increase)
        self.n_leaves += actual_leaf_increase
        self.log('nodes', self.n_nodes)
        self.log('leaves', self.n_leaves)
        self.log('lai', self.lai)

    def senescence(self, biomass_leaf, step_tt):
        # Leaf senescence
        leaves_senescing_per_node = self.plant.vars['fr_lf_sen_rate']
        node_senescence_rate = self.plant.vars['node_sen_rate']
        leaf_senescence = step_tt * (leaves_senescing_per_node * self.n_nodes) / node_senescence_rate
        self.n_leaves -= leaf_senescence
        self.log('leaf_senescence', leaf_senescence)

        # Leaf area (lai) senescence
        sen_age = leaf_senescence * (self.lai / self.n_leaves)
        sen_water_stress = 0
        sen_light_intensity = 0
        sen_frost = 0
        sen_heat = 0
        potential_lai_senescence = max(sen_age, sen_water_stress, sen_light_intensity, sen_frost, sen_heat)
        new_lai = max(self.plant.vars['min_tpla'], self.lai - potential_lai_senescence)
        lai_senescence = self.lai - new_lai
        self.lai -= lai_senescence
        self.log('lai_senescence', lai_senescence)

        # Biomass senescence
        biomass_senescence = biomass_leaf * (lai_senescence / self.lai)
        self.biomass_total -= biomass_senescence
        self.log('biomass_senescence', biomass_senescence)
