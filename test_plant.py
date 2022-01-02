import json
import pytest

from plant_model import Plant

def _load_file(fname):
    with open(fname) as f:
        return json.load(f)

def test_wheat_model():
    wheat_data = _load_file('data_files/wheat_data.json')
    env_data = _load_file('data_files/env_data.json')
    env_conditions = _load_file('data_files/default_env_conditions.json')
    wheat = Plant(wheat_data, env_data)
    def _step(n_steps):
        for i in range(n_steps):
            wheat.step(env_conditions)

    def _log(key, component=None):
        if component:
            if component in wheat.components:
                logs = wheat.components[component].logs
            else:
                for c in wheat.components:
                    if component in wheat.components[c].components:
                        logs = wheat.components[c].components[component].logs
        else:
            logs = wheat.logs
        assert len(logs) > 0
        return logs[key][-1]

    # SOWING
    assert wheat.phase_name == 'sowing'
    assert wheat.age == 0

    # GERMINATION
    _step(1)
    assert wheat.phase_name == 'germination'
    assert wheat.phase_day == 1

    # EMERGENCE
    _step(3)
    assert wheat.phase_name == 'emergence'
    assert wheat.phase_day == 1
    assert 'eme2ej' in wheat.phase_composite_phases
    # Initialize components
    for component in ['root', 'leaf', 'head', 'stem']:
        assert component in wheat.components
        assert wheat.components[component].biomass() >= 0
    for subcomponent in ['grain', 'pod']:
        assert subcomponent in wheat.components['head'].components
        assert wheat.components['head'].components[subcomponent].biomass() >= 0

    # END OF JUVENILE
    _step(1)
    assert wheat.phase_name == 'end_of_juvenile'
    assert 3 <= wheat.stage < 4
    assert wheat.phase_day == 1
    assert 'eme2ej' in wheat.phase_composite_phases
    # Genetic factors
    assert wheat.logs['photoperiod'][-1] == 0.904
    assert wheat.logs['vernalisation'][-1] == 0
    assert wheat.logs['vernalisation_factor'][-1] == 0.5759125

    # FLORAL INITIATION
    _step(27)
    assert wheat.phase_name == 'floral_initiation'
    assert wheat.phase_day == 1

    # FLOWERING
    _step(23)
    assert wheat.phase_name == 'flowering'
    assert wheat.phase_day == 1
    assert 'postflowering' in wheat.phase_composite_phases

    # START OF GRAIN FILLING
    _step(4)
    assert wheat.phase_name == 'start_of_grain_filling'
    assert wheat.phase_day == 1
    assert 'postflowering' in wheat.phase_composite_phases
    # Biomass accumulation
    assert _log('radiation_use_efficiency') == 1.24
    assert _log('intercepted_radiation') == 20
    assert _log('temperature_factor') == 0.5
    assert _log('nitrogen_factor') == 1
    assert _log('co2_factor') == 1.152005916126045
    assert _log('potential_biomass_accumulation') == 14.284873359962958
    assert _log('water_deficiency_factor') == 0.040287454882394706
    assert _log('actual_biomass_accumulation') == 0.5755011909902298
    # Biomass partition
    # assert _log('biomass_root', 'root') == 1
    # assert _log('biomass_head', 'head') == 1
    # assert _log('biomass_grain', 'grain') == 1
    # assert _log('biomass_pod_structural', 'pod') == 1
    # assert _log('biomass_pod_non_structural', 'pod') == 1
    # assert _log('biomass_leaf', 'leaf') == 1
    # assert _log('biomass_stem_structural', 'stem') == 1
    # assert _log('biomass_stem_non_structural', 'stem') == 1

    # END OF GRAIN FILLING
    _step(26)
    assert wheat.phase_name == 'end_of_grain_filling'
    assert wheat.phase_day == 1

    # HARVEST
    _step(1)
    assert wheat.phase_name == 'harvest_rips'
    assert wheat.phase_day == 1
