from typing import Literal, Optional, Self, TypedDict, Tuple
import numpy as np
from numpy.linalg import pinv
from scipy.interpolate import interp1d


class DifferentialPathlengthFactors(TypedDict):
    baby_head: float
    adult_head: float
    adult_arm: float
    adult_leg: float


DpfType = Literal["baby_head", "adult_head", "adult_arm", "adult_leg"]


class MBLConstants:
    """Class for holding MBL constants"""

    # Differential path length factors based on Dunan 1994
    _dpf_dict: DifferentialPathlengthFactors = {
        "baby_head": 4.99,
        "adult_head": 6.26,
        "adult_arm": 4.16,
        "adult_leg": 5.51,
    }

    def __init__(
        self,
        extinction_coefficients: np.ndarray,
        wavelength_dependency_of_pathlength: np.ndarray,
        optode_dist: float,
        dpf_type: DpfType,
        wavelengths: Tuple[int, int],
    ) -> None:
        self.extinction_coefficients = extinction_coefficients
        self.wavelength_dependency = wavelength_dependency_of_pathlength
        self.optode_dist = optode_dist
        self.dpf: float = self._dpf_dict[dpf_type]

        (min_wavelength, max_wavelength) = wavelengths
        self.interp_wavelengths: np.ndarray = np.arange(
            min_wavelength, max_wavelength + 1
        )


class MBL:
    """Class for calculating conc. using the Modified Beer-Lambert Law"""

    def __init__(self, constants: MBLConstants) -> None:
        self.constants: MBLConstants = constants
        self.attenuation_interp_wavelength_dependency: Optional[
            np.ndarray
        ] = None

    def _calc_change_in_attenuation(
        self, spectra: np.ndarray, spectra_wavelengths: np.ndarray
    ) -> Self:
        n_spectra = spectra.shape[0]
        attenuation: np.ndarray = np.zeros(spectra.shape)
        attenuation_interp: np.ndarray = np.zeros(
            (self.constants.interp_wavelengths.size, n_spectra)
        )

        for i in range(n_spectra):
            attenuation[i, :]: np.ndarray = np.log10(
                spectra[0, :] / spectra[i, :]
            )
            attenuation_interp[:, i] = interp1d(
                spectra_wavelengths,
                attenuation[i, :].T,
                kind="cubic",
            )(self.constants.interp_wavelengths)

        self.attenuation_interp_wavelength_dependency = np.divide(
            attenuation_interp.T, self.constants.wavelength_dependency
        )

    def calc_concentrations(
        self, spectra: np.ndarray, spectra_wavelengths: np.ndarray
    ) -> np.ndarray:
        # Calculate change in attenuation
        self._calc_change_in_attenuation(spectra, spectra_wavelengths)

        # Calculate concentration of species
        ext_coeffs_inv: np.ndarray = pinv(
            self.constants.extinction_coefficients
        )
        optode_dist = self.constants.optode_dist
        dpf = self.constants.dpf

        return np.transpose(
            np.matmul(
                ext_coeffs_inv,
                self.attenuation_interp_wavelength_dependency.T,
            )
            * (1 / (optode_dist * dpf))
        )
