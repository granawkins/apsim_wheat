import math
from utils import interpolate
from components import BaseComponent, Root, Leaf, Head, Stem

class Plant(BaseComponent):

    def __init__(self, plant_data, env_data):
        """

        Wheat plant data source: https://github.com/APSIMInitiative/APSIMClassic/blob/master/Model/Wheat.xml
        """
        super().__init__(self)

        # Initialize lifetime variables
        self.age = 0
        self.vernalisation = 0
        self.terminated = False
        self.termination_reason = ''

        # Initialize phase data
        self.phase_index = []
        self.phase_dict = {}
        phases = plant_data.pop('phases')
        composite_phases = plant_data.pop('composite_phases')
        for name, value in phases:
            self.phase_index.append(name)
            self.phase_dict[name] = dict(thermal_time=value, composite_phases=[], termination=[])
        for name, incl_phases in composite_phases.items():
            for phase in incl_phases:
                self.phase_dict[phase]['composite_phases'].append(name)

        # Calculate germination time based on sowing depth
        sowing_depth = env_data.pop('sowing_depth')
        shoot_lag = plant_data.pop('shoot_lag')
        shoot_rate = plant_data.pop('shoot_rate')
        germ_tt = shoot_lag + sowing_depth * shoot_rate  # Equation 7
        self.phase_dict['germination']['thermal_time'] = germ_tt

        # Initialize termination cases
        self.termination = []
        germ_limit = plant_data.pop('days_germ_limit', None)
        if germ_limit:
            self.phase_dict['sowing']['termination'].append(dict(limit=germ_limit, unit='days'))
        emerg_limit = plant_data.pop('tt_emerg_limit', None)
        if emerg_limit:
            self.phase_dict['germination']['termination'].append(dict(limit=emerg_limit, unit='thermal_time'))

        # Load remaining variables into self
        self.row_spacing = env_data['row_spacing']
        self.phase_modifiers = plant_data.pop('phase_modifiers')
        self.vars = plant_data
        self._set_phase(0)


    def step(self, env_conditions):
        """Increments the plant's life by 1 day based on supplied environmental conditions"""

        self.age += 1
        env_conditions['air_temp_mean'] = (env_conditions['air_temp_max'] - env_conditions['air_temp_min']) / 2

        # Calculate available thermal time
        step_tt = self._calc_thermal_time(env_conditions)

        # Update growth phase progress
        while step_tt > 0:
            if self.phase_name == 'sowing':
                if env_conditions.get('soil_water', 0) >= self.vars['pesw_germ']:
                    self._set_phase(self.phase_number + 1)
                else:
                    self.phase_tt += step_tt
                    break
            elif step_tt >= self.phase_remaining_tt:
                step_tt -= self.phase_remaining_tt
                self._set_phase(self.phase_number + 1)
            else:
                self.phase_tt += step_tt
                self.phase_remaining_tt -= step_tt
                self.stage = self.phase_number + (self.phase_tt / self.phase_total_tt)
                break
        self.phase_day += 1
        self.log('phase_day', self.phase_day)
        self.log('phase_tt', self.phase_tt)
        self.log('phase_remaining_tt', self.phase_remaining_tt)
        self.log('stage', self.stage)

        # Update biomass
        accumulated_biomass = self._calc_biomass_accumulation(env_conditions)
        self.log('biomass_total', self.biomass())
        if accumulated_biomass > 0:
            self._calc_biomass_partition(accumulated_biomass, env_conditions, step_tt)

        # Check termination cases
        for case in self.phase_termination:
            if case['unit'] == 'days':
                source = self.phase_day
            elif case['unit'] == 'thermal_time':
                source = self.phase_tt
            if source >= case['limit']:
                self.kill(f"Killed in {self.phase_name}: {case['unit']} exceeded {case['limit']}.")

    def kill(self, reason):
        self.terminated = True
        self.termination_reason = reason


    def get_logs(self):
        logs = {}
        def _add_logs(key, obj):
            logs[key] = obj.logs
            if obj.components and len(obj.components) > 1:
                for comp_key, comp_obj in obj.components.items():
                    _add_logs(comp_key, comp_obj)
        _add_logs('plant', self)
        return logs


    def _set_phase(self, i):
        """Updates the phase given a new index"""

        # Reset phase lifetime variables
        self.phase_day = 0
        self.phase_tt = 0

        # Load current phase data
        self.phase_number = i
        self.stage = i
        self.phase_name = self.phase_index[i]
        phase = self.phase_dict[self.phase_name]
        self.phase_total_tt = phase['thermal_time']
        self.phase_remaining_tt = phase['thermal_time']
        self.phase_composite_phases = phase['composite_phases']
        self.phase_termination = phase['termination']

        # Misc
        if self.phase_name == 'emergence':
            self._init_components()


    def _init_components(self):
        self.components['root'] = Root(self)
        self.components['leaf'] = Leaf(self)
        self.components['head'] = Head(self)
        self.components['stem'] = Stem(self)

    def _calc_thermal_time(self, env_conditions):
        """Calculate thermal time in degree-days, the primary growth metric"""

        # 1. Calculate crown temperature
        t_max = env_conditions['air_temp_max']
        t_min = env_conditions['air_temp_min']
        snow_height = env_conditions['snow_height']
        def _sub_zero(temp):
            return 2 + temp * (0.4 + 0.0018 * (snow_height - 15) ** 2)
        crown_t_max = t_max if t_max >= 0 else _sub_zero(t_max)  # Equation 1
        crown_t_min = t_min if t_min >= 0 else _sub_zero(t_min)  # Equation 2
        crown_t_mean = (crown_t_max + crown_t_min) / 2           # Equation 3
        self.log('crown_t_mean', crown_t_mean)

        # 2. Calculate base thermal time
        if crown_t_mean <= 0:  # Equation 4
            thermal_time = 0
        elif crown_t_mean <= 26:
            thermal_time = crown_t_mean
        elif crown_t_mean <= 34:
            thermal_time = 26 / 8 * (34 - crown_t_mean)
        else:
            thermal_time = 0
        self.log('tt_base', thermal_time)

        # 3. Adjust for genetic factors
        if 'eme2ej' in self.phase_composite_phases:
            # Photoperiod penalizes growth based on the amount of available daylight
            day_length = env_conditions['day_length']
            photoperiod = 1 - 0.002 * self.vars['photop_sens'] * (20 - day_length) ** 2  # Equation 8
            self.log('photoperiod', photoperiod)

            # Vernalization penalizes growth if temperature is too cold or hot
            if t_max < 30 and t_min < 15:  # Equation 9, 11
                v0 = 1.4 - 0.0778 * crown_t_mean
                v1 = 0.5 + 13.44 * (crown_t_mean / ((t_max - t_min + 3) ** 2))
                self.vernalisation += min(v0, v1)
            elif t_max > 30 and self.vernalisation < 10:  # Equation 10, 11
                v0 = 0.5 * (t_max - 30)
                self.vernalisation -= min(v0, self.vernalisation)
            vernalisation_factor = 1 - (0.0054545 * self.vars['vern_sens'] + 0.0003) * (50 - self.vernalisation)  # Equation 12
            self.log('vernalisation', self.vernalisation)
            self.log('vernalisation_factor', vernalisation_factor)

            # Thermal time limited by the lowest of these
            thermal_time = thermal_time * min(photoperiod, vernalisation_factor)  # Equation 6
        self.log('tt_adj_gen', thermal_time)

        # 4. Adjust for environmental factors
        soil_water_stress = 1
        nitrogen_stress = 1
        phosphorus_stress = 1
        environmental_factors = min(soil_water_stress, nitrogen_stress, phosphorus_stress)
        thermal_time = thermal_time * environmental_factors  # Equation 5
        self.log('tt_adj_env', thermal_time)

        return thermal_time


    def _calc_biomass_accumulation(self, env_conditions):
        """Calculates the increase in stored biomass based on current growth and environmental factors"""

        radiation_use_efficiency = interpolate(self.phase_modifiers['x_stage_rue'],
                                               self.phase_modifiers['y_rue'],
                                               self.stage)
        if radiation_use_efficiency == 0:
            return 0
        self.log('radiation_use_efficiency', radiation_use_efficiency)

        # 1. Potential Biomass Accumulation
        # 1a. Intercepted Radiation
        total_radiation = env_conditions['total_radiation']
        extinction_coefficient = interpolate(self.vars['x_row_spacing'],
                                             self.vars['y_extinct_coef'],
                                             self.row_spacing)
        leaf_area_index = self.components['leaf'].lai
        intercepted_radiation = total_radiation * (1 - math.exp(-extinction_coefficient * leaf_area_index))
        self.log('intercepted_radiation', intercepted_radiation)

        # 1b. Stress Factor
        # 1bi. Temperature Factor
        air_temp_mean = env_conditions['air_temp_mean']
        temperature_factor = interpolate(self.vars['x_ave_temp'],
                                         self.vars['y_stress_photo'],
                                         air_temp_mean)
        self.log('temperature_factor', temperature_factor)

        # # 1bii. Nitrogen Factor
        # n_conc_min_leaf = interpolate(self.phase_modifiers['x_stage_code'],
        #                               self.phase_modifiers['y_n_conc_min_leaf'],
        #                               self.stage)
        # n_conc_crit_leaf = interpolate(self.phase_modifiers['x_stage_code'],
        #                                self.phase_modifiers['y_n_conc_crit_leaf'],
        #                                self.stage)
        # leaf_nitrogen = 0
        # leaves = [
        #     {'alive': True, 'lai': 1000, 'nitrogen_concentration': 0.05},
        #     {'alive': False, 'lai': 500, 'nitrogen_concentration': 0.05}
        # ]
        # for leaf in leaves:
        #     leaf_n = (leaf['nitrogen_concentration'] - n_conc_min_leaf) / (n_conc_crit_leaf - n_conc_min_leaf)
        #     leaf_nitrogen += leaf_n
        # nitrogen_factor  self.vars['N_fact_photo'] * leaf_nitrogen
        nitrogen_factor = 1
        self.log('nitrogen_factor', nitrogen_factor)

        stress_factor = min(temperature_factor, nitrogen_factor)

        # 1c. CO2 Factor
        c = env_conditions['co2_concentration']
        ci = (163 - air_temp_mean) / (5 - 0.1 * air_temp_mean)
        co2_factor = ((c - ci) * (350 + 2 * ci)) / ((c + 2 * ci) * (350 - ci))
        self.log('co2_factor', co2_factor)

        potential_biomass_accumulation = \
            intercepted_radiation * \
            radiation_use_efficiency * \
            stress_factor * \
            co2_factor
        self.log('potential_biomass_accumulation', potential_biomass_accumulation)

        # 2. Soil Water Deficiency
        # 2a. Transpiration efficiency from co2 concentration
        transpiration_efficiency_factor = interpolate(self.vars['x_co2_te_modifier'],
                                                      self.vars['y_co2_te_modifier'],
                                                      env_conditions['co2_concentration'])
        self.log('transpiration_efficiency_factor', transpiration_efficiency_factor)
        # 2b. Vapor Pressure Deficit
        saturated_vapour_pressure = self.vars['svp_fract']
        def f_vpd(t):
            return 6.1078 * math.exp((17.269 * t) / (237.3 + t))
        vapour_pressure_deficit = saturated_vapour_pressure * \
            (f_vpd(env_conditions['air_temp_max']) - f_vpd(env_conditions['air_temp_min']))
        self.log('vapour_pressure_deficit', vapour_pressure_deficit)
        # 2c. Transpiration efficiency
        transpiration_efficiency_coefficient = interpolate(self.phase_modifiers['x_stage_rue'],
                                                           self.phase_modifiers['transp_eff_cf'],
                                                           self.stage)
        self.log('transpiration_efficiency_coefficient', transpiration_efficiency_coefficient)
        transpiration_efficiency_modifier = transpiration_efficiency_coefficient / vapour_pressure_deficit
        transpiration_efficiency = transpiration_efficiency_factor * transpiration_efficiency_modifier
        self.log('transpiration_efficiency', transpiration_efficiency)

        # 2b. Water demand
        respiration_rate = 0
        water_demand = (potential_biomass_accumulation - respiration_rate) / transpiration_efficiency
        self.log('water_demand', water_demand)
        water_uptake = min(water_demand, env_conditions['soil_water'])
        water_deficiency_factor = water_uptake / water_demand
        self.log('water_deficiency_factor', water_deficiency_factor)

        # 3. Actual
        actual_biomass_accumulation = potential_biomass_accumulation * water_deficiency_factor
        self.log('actual_biomass_accumulation', actual_biomass_accumulation)

        return actual_biomass_accumulation

    def _calc_biomass_partition(self, biomass_accumulation, env_conditions, step_tt):

        # Flow through components
        remainder = self.components['root'].partition(biomass_accumulation, env_conditions)
        remainder = self.components['head'].partition(remainder, env_conditions, biomass_accumulation)
        remainder = self.components['leaf'].partition(remainder, step_tt)
        self.components['stem'].partition(remainder)

        # RE-TRANSLOCATION
        unfulfilled = self.components['head'].unfulfilled()
        self.log('unfulfilled', unfulfilled)
        if unfulfilled == 0:
            return

        retranslocated_from_stem = self.components['stem'].retranslocate_from(unfulfilled)
        unfulfilled -= retranslocated_from_stem

        retranslocated_from_head = self.components['head'].retranslocate_from(unfulfilled)
        unfulfilled -= retranslocated_from_stem

        retranslocated = retranslocated_from_stem + retranslocated_from_head
        self.components['head'].retranslocate_to(retranslocated)
