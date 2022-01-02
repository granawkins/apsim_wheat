class BaseComponent:

    def __init__(self, plant, parent=None):
        self.plant = plant
        self.parent = parent
        self.components = {}
        self.logs = {}

        self.biomass_total = 0
        self.biomass_structural = 0
        self.biomass_non_structural = 0
        self.unfulfilled_total = 0

    def log(self, field, value):
        if field not in self.logs:
            self.logs[field] = []
        log = self.logs[field]
        while len(log) < self.plant.age - 1:
            log.append(0)
        log.append(value)

    def biomass(self, subtype=None):
        if not subtype:
            return self.biomass_total + sum([c.biomass() for c in self.components.values()])
        elif subtype == 'structural':
            return self.biomass_structural + sum([c.biomass(subtype) for c in self.components.values()])
        elif subtype == 'non_structural':
            return self.biomass_non_structural + sum([c.biomass(subtype) for c in self.components.values()])
        else:
            raise Exception("Unknown biomass subtype:", subtype)

    def unfulfilled(self):
        return self.unfulfilled_total + sum([c.unfulfilled() for c in self.components.values()])
