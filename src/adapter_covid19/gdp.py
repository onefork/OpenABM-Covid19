import abc
import copy
import itertools
import logging
import random
from dataclasses import dataclass
from typing import Tuple, Mapping, MutableMapping, Sequence

import numpy as np
from scipy.optimize import linprog

from adapter_covid19.constants import START_OF_TIME, DAYS_IN_A_YEAR
from adapter_covid19.datasources import (
    Reader,
    RegionSectorAgeDataSource,
    SectorDataSource,
    WeightMatrix,
    DataSource,
)
from adapter_covid19.enums import Region, Sector, Age


LOGGER = logging.getLogger(__name__)


@dataclass
class GdpResult:
    gdp: MutableMapping[int, Mapping[Tuple[Region, Sector, Age], float]]  # G
    workers: MutableMapping[int, Mapping[Tuple[Region, Sector, Age], float]]  # n
    max_gdp: float
    max_workers: float

    def fraction_gdp_by_sector(self, time: int) -> Mapping[Sector, float]:
        return {
            s: sum(
                self.gdp[time][r, s, a] / self.max_gdp
                for r, a in itertools.product(Region, Age)
            )
            for s in Sector
        }


class BaseGDPBackboneMixin(abc.ABC):
    beta: Mapping[Sector, float]

    @abc.abstractmethod
    def load(self, reader: Reader) -> None:
        pass

    def adjust_gdp(
        self, time: int, gdp: Mapping[Tuple[Region, Sector, Age], float],
    ) -> Mapping[Tuple[Region, Sector, Age], float]:
        return {
            (r, s, a): gdp[(r, s, a)]
            * (1 + self.beta.get(s, 0.0) * (time - START_OF_TIME) / DAYS_IN_A_YEAR)
            for (r, s, a) in gdp.keys()
        }


class LinearGDPBackboneMixin(BaseGDPBackboneMixin):
    def load(self, reader: Reader) -> None:
        super().load(reader)
        self.beta = SectorDataSource("growth_rates").load(reader)


class BaseGdpModel(abc.ABC):
    gdp: Mapping[Tuple[Region, Sector, Age], float]
    workers: Mapping[Tuple[Region, Sector, Age], float]
    keyworker: Mapping[Sector, float]

    def __init__(self, lockdown_recovery_time: int = 1, optimal_recovery: bool = False):
        self.lockdown_recovery_time = lockdown_recovery_time
        self.optimal_recovery = optimal_recovery
        self.recovery_order: Sequence[Tuple[Region, Sector, Age]] = []
        self.results = GdpResult({}, {}, 0, 0)
        self.datasources = self._get_datasources()
        for k, v in self.datasources.items():
            self.__setattr__(k, None)

    @property
    def max_gdp(self):
        return self.results.max_gdp

    @property
    def max_workers(self):
        return self.results.max_workers

    @abc.abstractmethod
    def _get_datasources(self) -> Mapping[str, DataSource]:
        # TODO: This should really be a functools.cached_property, but no python 3.8
        datasources = {
            "gdp": RegionSectorAgeDataSource,
            "workers": RegionSectorAgeDataSource,
            "keyworker": SectorDataSource,
        }
        return {k: v(k) for k, v in datasources.items()}

    def _check_data(self) -> None:
        """
        Checks that sectors, regions and ages are consistent between data
        :return:
        """
        if "gdp" not in self.datasources:
            raise ValueError("Trying to simulate gdp without gdp...?")
        for k, v in self.datasources.items():
            if isinstance(v, RegionSectorAgeDataSource):
                regions, sectors, ages = [
                    set(x) for x in zip(*list(self.__getattribute__(k).keys()))
                ]
                if regions != set(Region):
                    raise ValueError(f"Inconsistent data for {k}: {regions}, {Region}")
                if sectors != set(Sector):
                    raise ValueError(f"Inconsistent data for {k}: {sectors}, {Sector}")
                if ages != set(Age):
                    raise ValueError(f"Inconsistent data for {k}: {ages}, {Age}")
            elif isinstance(v, SectorDataSource):
                sectors = set(self.__getattribute__(k).keys())
                if sectors != set(Sector):
                    raise ValueError(f"Inconsistent data for {k}: {sectors}, {Sector}")
            elif isinstance(v, WeightMatrix):
                matrix = self.__getattribute__(k)
                if any(len(Sector) != s for s in matrix.shape):
                    raise ValueError(
                        f"Inconsistent data for {k}: {len(Sector)}, {matrix.shape}"
                    )
            else:
                raise NotImplementedError(
                    f"Data checks not implemented for {v.__class__.__name__}"
                )

    def load(self, reader: Reader):
        super().load(reader)
        for k, v in self.datasources.items():
            self.__setattr__(k, v.load(reader))
        self._check_data()
        self.results.max_gdp = sum(
            self.gdp[key] for key in itertools.product(Region, Sector, Age)
        )
        self.results.max_workers = sum(
            self.workers[key] for key in itertools.product(Region, Sector, Age)
        )
        gdp_per_worker = {k: self.gdp[k] / self.workers[k] for k in self.gdp}
        # Sort in terms of greatest productivity to least productivity
        self.recovery_order = sorted(
            gdp_per_worker, key=lambda x: gdp_per_worker[x], reverse=True
        )
        if not self.optimal_recovery:
            random.shuffle(self.recovery_order)

    def _apply_lockdown(
        self,
        time: int,
        lockdown: bool,
        lockdown_exit_time: int,
        utilisations: Mapping[Tuple[Region, Sector, Age], float],
    ) -> Mapping[Tuple[Region, Sector, Age], float]:
        base_utilisations = {
            (r, s, a): u * self.keyworker[s] for (r, s, a), u in utilisations.items()
        }
        if lockdown:
            utilisations = base_utilisations
        elif lockdown_exit_time:
            full_utilisations = copy.deepcopy(utilisations)
            full_workers = sum(
                self.workers[k] * utilisations[k]
                for k in itertools.product(Region, Sector, Age)
            )
            current_workers = key_workers = sum(
                self.workers[k] * base_utilisations[k]
                for k in itertools.product(Region, Sector, Age)
            )
            utilisations = copy.deepcopy(base_utilisations)
            recovery_factor = min(
                (time - lockdown_exit_time) / self.lockdown_recovery_time, 1
            )
            to_send_back = key_workers + (full_workers - key_workers) * recovery_factor
            for key in self.recovery_order:
                if current_workers >= to_send_back:
                    break
                spare_capacity = (
                    full_utilisations[key] - utilisations[key]
                ) * self.workers[key]
                increase = min(spare_capacity, to_send_back - current_workers)
                utilisations[key] += increase / self.workers[key]
                if utilisations[key] > 1:
                    raise ValueError(f"Utilisation > 1: {key}: {utilisations[key]}")
                current_workers += increase
        return utilisations

    @abc.abstractmethod
    def simulate(
        self,
        time: int,
        lockdown: bool,
        lockdown_exit_time: int,
        utilisations: Mapping[Tuple[Region, Sector, Age], float],
    ) -> None:
        # utilisations = self._apply_lockdown(time, lockdown, lockdown_exit_time, utilisations)
        pass


class LinearGdpModel(BaseGdpModel, LinearGDPBackboneMixin):
    gdp: Mapping[Tuple[Region, Sector, Age], float]
    workers: Mapping[Tuple[Region, Sector, Age], float]
    wfh: Mapping[str, float]
    vulnerability: Mapping[str, float]

    def __init__(self, lockdown_recovery_time: int = 1, optimal_recovery: bool = False):
        super().__init__(lockdown_recovery_time, optimal_recovery)

    def _get_datasources(self) -> Mapping[str, DataSource]:
        datasources = {
            "gdp": RegionSectorAgeDataSource,
            "workers": RegionSectorAgeDataSource,
            "keyworker": SectorDataSource,
            "vulnerability": SectorDataSource,
            "wfh": SectorDataSource,
        }
        return {k: v(k) for k, v in datasources.items()}

    def _simulate_gdp(
        self, region: Region, sector: Sector, age: Age, utilisation: float
    ) -> float:
        wfh_factor = self.wfh[sector]
        vulnerability_factor = self.vulnerability[sector]
        return (
            wfh_factor + (vulnerability_factor - wfh_factor) * utilisation
        ) * self.gdp[region, sector, age]

    def _simulate_workers(
        self, region: Region, sector: Sector, age: Age, utilisation: float
    ) -> float:
        return utilisation * self.workers[region, sector, age]

    def simulate(
        self,
        time: int,
        lockdown: bool,
        lockdown_exit_time: int,
        utilisations: Mapping[Tuple[Region, Sector, Age], float],
    ) -> None:
        utilisations = self._apply_lockdown(
            time, lockdown, lockdown_exit_time, utilisations
        )

        gdp = {
            (r, s, a): self._simulate_gdp(r, s, a, u)
            for (r, s, a), u in utilisations.items()
        }
        workers = {
            (r, s, a): self._simulate_workers(r, s, a, u)
            for (r, s, a), u in utilisations.items()
        }
        if not lockdown:
            gdp = self.adjust_gdp(time, gdp)
        self.results.gdp[time] = gdp
        self.results.workers[time] = workers


class SupplyDemandGdpModel(BaseGdpModel, LinearGDPBackboneMixin):
    gdp: Mapping[Tuple[Region, Sector, Age], float]
    workers: Mapping[Tuple[Region, Sector, Age], float]
    wfh: Mapping[Sector, float]
    vulnerability: Mapping[Sector, float]
    supply: np.array
    demand: np.array

    def __init__(
        self,
        lockdown_recovery_time: int = 1,
        optimal_recovery: bool = False,
        theta: float = 1.2,
    ):
        super().__init__(lockdown_recovery_time, optimal_recovery)
        self.theta = theta

    def _get_datasources(self) -> Mapping[str, DataSource]:
        datasources = {
            "gdp": RegionSectorAgeDataSource,
            "workers": RegionSectorAgeDataSource,
            "keyworker": SectorDataSource,
            "vulnerability": SectorDataSource,
            "wfh": SectorDataSource,
            "supply": WeightMatrix,
            "demand": WeightMatrix,
        }
        return {k: v(k) for k, v in datasources.items()}

    def _simulate_gdp(
        self, utilisations: Mapping[Tuple[Region, Sector, Age], float],
    ) -> Mapping[Tuple[Region, Sector, Age], float]:
        """
        Refer to the model docs for documentation of this function
        :param utilisations:
        :return: GDP per region, sector, age
        """
        # Reforumlate the problem in terms of Region, Age, Sector (makes easier to solve)
        gdp = {}
        for region, age in itertools.product(Region, Age):
            lam = np.array([utilisations[region, s, age] for s in Sector])
            n = len(Sector)
            c = -np.array([self.gdp[region, s, age] for s in Sector])
            h = {s: self.wfh[s] for s in Sector}
            H = np.array([self.wfh[s] for s in Sector])
            WY = self.supply
            WD = self.demand
            bounds = [(0, 1) for _ in range(n)]
            y_max = {
                si: sum(WY[i, j] * (1 - h[sj]) for j, sj in enumerate(Sector))
                for i, si in enumerate(Sector)
            }
            d_max = {
                si: sum(WD[i, j] * (1 - h[sj]) for j, sj in enumerate(Sector))
                for i, si in enumerate(Sector)
            }
            alpha_hat = np.array(
                [
                    (1 - h[s] * self.theta) / min(d_max[s], y_max[s])
                    if h[s] != 1
                    else 1
                    for s in Sector
                ]
            )
            alphalam = np.diag(alpha_hat * lam)
            ialphalamwy = np.eye(n) - alphalam.dot(WY)
            ialphalamwd = np.eye(n) - alphalam.dot(WD)
            aub = np.vstack([ialphalamwy, ialphalamwd,])
            bub = np.concatenate(
                [
                    (
                        np.eye(n) - (1 - self.theta) * np.diag(lam) - alphalam.dot(WY)
                    ).dot(H),
                    (
                        np.eye(n) - (1 - self.theta) * np.diag(lam) - alphalam.dot(WD)
                    ).dot(H),
                ]
            )
            if aub[n - 1, -1] == 0:
                aub[n - 1, -1] = 1
                aub[2 * n - 1, -1] = 1
                bub[n - 1] = 1
                bub[2 * n - 1] = 1
            r = linprog(
                c=c,
                A_ub=aub,
                b_ub=bub,
                bounds=bounds,
                x0=None,
                method="revised simplex",
            )
            if not r.success:
                raise ValueError(r.message)
            for x, sector in zip(r.x, Sector):
                gdp[region, sector, age] = x * self.gdp[region, sector, age]
        return gdp

    def _simulate_workers(
        self, region: Region, sector: Sector, age: Age, utilisation: float
    ) -> float:
        return utilisation * self.workers[region, sector, age]

    def simulate(
        self,
        time: int,
        lockdown: bool,
        lockdown_exit_time: int,
        utilisations: Mapping[Tuple[Region, Sector, Age], float],
    ) -> None:
        utilisations = self._apply_lockdown(
            time, lockdown, lockdown_exit_time, utilisations
        )

        workers = {
            (r, s, a): self._simulate_workers(r, s, a, u)
            for (r, s, a), u in utilisations.items()
        }
        gdp = self._simulate_gdp(utilisations)
        if not lockdown:
            gdp = self.adjust_gdp(time, gdp)
        self.results.gdp[time] = gdp
        self.results.workers[time] = workers
