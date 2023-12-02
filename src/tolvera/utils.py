'''
TODO: Save/load
'''

import os
from pathlib import Path
from typing import Any, Union, Tuple
import unicodedata
import torch
import numpy as np
import jsons
import base64
import time

import taichi as ti
from taichi.lang.field import ScalarField
from taichi._lib.core.taichi_python import DataType

def rand(n, factor=0.5):
    return torch.rand(n) * factor

def rand_uniform(n, low=0.0, high=1.0):
    return torch.rand(n) * (high - low) + low

def rand_normal(n, mean=0.0, std=1.0):
    return torch.randn(n) * std + mean

def rand_exponential(n, lambd=1.0):
    return torch.rand(n).exponential_(lambd)

def rand_cauchy(n, median=0.0, sigma=1.0):
    return torch.randn(n).cauchy_(median, sigma)

def rand_lognormal(n, mean=0.0, std=1.0):
    return torch.randn(n).log_normal_(mean, std)

def rand_sigmoid(n, factor=0.5):
    tensor = rand(n, factor)
    return torch.sigmoid(tensor)

def rand_beta(n, theta, beta):
    dist = torch.distributions.beta.Beta(theta, beta)
    return dist.sample((n,))

"""
def np_rand(n, factor=0.5):
    return np.random.rand(n) * factor

def np_rand_uniform(n, low=0.0, high=1.0):
    return np.random.uniform(low, high, n)

def np_rand_normal(n, mean=0.0, std=1.0):
    return np.random.normal(mean, std, n)

def np_rand_exponential(n, lambd=1.0):
    return np.random.exponential(1 / lambd, n)

def np_rand_lognormal(n, mean=0.0, std=1.0):
    return np.random.lognormal(mean, std, n)

def np_rand_sigmoid(n, factor=0.5):
    tensor = np_rand(n, factor)
    return sigmoid(tensor)

def np_rand_beta(n, alpha, beta):
    return np.random.beta(alpha, beta, n)
"""

def remove_accents(input: str):
    nfkd_form = unicodedata.normalize('NFKD', input)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def clean_name(name: str):
    return remove_accents(name).strip().lower()

# @ti.data_oriented
class CONSTS:
    '''
    Dict of CONSTS that can be used in Taichi scope
    '''
    def __init__(self, dict: dict[str, (DataType, Any)]):
        self.struct = ti.types.struct(**{k: v[0] for k, v in dict.items()})
        self.consts = self.struct(**{k: v[1] for k, v in dict.items()})
    def __getattr__(self, name):
        try:
            return self.consts[name]
        except:
            raise AttributeError(f"CONSTS has no attribute {name}")
    def __getitem__(self, name):
        try:
            return self.consts[name]
        except:
            raise AttributeError(f"CONSTS has no attribute {name}")

def ndarray_b64_serialize(ndarray):
    return {
        "@type": "ndarray",
        "dtype": str(ndarray.dtype),
        "shape": ndarray.shape,
        "b64": base64.b64encode(ndarray.tobytes()).decode('utf-8')
    }

def ndarray_b64_deserialize(serialized):
    return np.frombuffer(base64.b64decode(serialized["b64"]), dtype=np.dtype(serialized["dtype"])).reshape(serialized["shape"])

def np_serialize(ndarray):
    return jsons.dumps(ndarray_b64_serialize(ndarray))

def np_deserialize(json_str):
    return ndarray_b64_deserialize(jsons.loads(json_str))

def ti_serialize(field):
    if isinstance(field, (ScalarField, ti.lang.struct.StructField, ti.lang.matrix.MatrixField, ti.lang.matrix.VectorNdarray, ti.lang._ndarray.ScalarNdarray)):
        ndarray = field.to_numpy()
        if isinstance(ndarray, dict): # For StructField where to_numpy() returns a dict
            serialized = jsons.dumps({k: ndarray_b64_serialize(v) for k, v in ndarray.items()})
        else: # For other fields
            serialized = jsons.dumps(ndarray_b64_serialize(ndarray))
        field.serialized = serialized
        return serialized
    else:
        raise TypeError(f"Unsupported field type for serialization: {type(field)}")

def ti_deserialize(field, json_str):
    if isinstance(field, (ScalarField, ti.lang.struct.StructField, ti.lang.matrix.MatrixField, ti.lang.matrix.VectorNdarray, ti.lang._ndarray.ScalarNdarray)):
        data = jsons.loads(json_str)
        if isinstance(field, ti.lang.struct.StructField): # For StructField
            field.from_numpy({k: ndarray_b64_deserialize(v) for k, v in data.items()})
        else: # For other fields
            field.from_numpy(ndarray_b64_deserialize(data))
        field.serialized = None
    else:
        raise TypeError(f"Unsupported field type for deserialization: {type(field)}")

def time_function(func, *args, **kwargs):
    """Time how long it takes to run a function and print the result
    """
    start = time.time()
    func(*args, **kwargs)
    end = time.time()
    print(f"[Tolvera.utils] {func.__name__}() ran in {end-start:.4f}s")
    return end-start

def validate_path(path: str) -> bool:
    """
    Validate a path using os.path and pathlib.

    Args:
        path (str): The path to be validated.

    Returns:
        bool: True if the path is valid, raises an exception otherwise.

    Raises:
        TypeError: If the input is not a string.
        FileNotFoundError: If the path does not exist.
        PermissionError: If the path is not accessible.
    """
    if not isinstance(path, str):
        raise TypeError(f"Expected a string for path, but received {type(path)}")

    path_obj = Path(path)
    if not path_obj.is_file():
        raise FileNotFoundError(f"The path {path} does not exist or is not a file")

    if not os.access(path, os.R_OK):
        raise PermissionError(f"The path {path} is not accessible")

    return True

def validate_json_path(path: str) -> bool:
    """
    Validate a JSON file path. It uses validate_path for initial validation.

    Args:
        path (str): The JSON file path to be validated.

    Returns:
        bool: True if the path is a valid JSON file path, raises an exception otherwise.

    Raises:
        ValueError: If the path does not end with '.json'.
    """
    # Using validate_path for basic path validation
    validate_path(path)

    if not path.endswith('.json'):
        raise ValueError("Path should end with '.json'")

    return True

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

def flatten(lst):
    """Flatten a nested list or return a non-nested list as is."""
    if all(isinstance(el, list) for el in lst):
        return [item for sublist in lst for item in sublist]
    return lst

def monkey_patch_cls_methods(target_class, source_instance):
    for attr_name in dir(source_instance):
        if callable(getattr(source_instance, attr_name)) and not attr_name.startswith("__"):
            setattr(target_class, attr_name, getattr(source_instance, attr_name))

class Lag:
    def __init__(self, val:Any=None, coef:float=0.5):
        self.coef = coef
        self.val = val
    def __call__(self, val:Any, coef:float=None):
        if coef is not None: self.coef = coef
        if self.val is None: self.val = val
        else: self.val = self._update_val(self.val, val)
        return self.val
    def _update_val(self, old:Any, new:Any):
        assert type(old) is type(new), f"old type '{type(old)}' != new type '{type(new)}'"
        assert old is not None, f"old is None"
        assert new is not None, f"new is None"
        if isinstance(old, float):
            return old * self.coef + new * (1 - self.coef)
        elif isinstance(old, list):
            return [v * self.coef + n * (1 - self.coef) for v, n in zip(old, new)]
        elif isinstance(old, np.ndarray):
            return np.add(np.multiply(old, self.coef), np.multiply(new, 1 - self.coef))
        elif torch.is_tensor(old):
            return old * self.coef + new * (1 - self.coef)
        else:
            raise TypeError(f"Unsupported Lag type: '{type(old)}'.")

def create_and_validate_slice(arg: Union[int, Tuple[int, ...], slice], target_array: np.ndarray) -> slice:
    """
    Creates and validates a slice object based on the target array.
    """
    try:
        slice_obj = create_safe_slice(arg)
        if not validate_slice(slice_obj, target_array):
            raise ValueError(f"Invalid slice: {slice_obj}")
        return slice_obj
    except TypeError as e:
        print(f"TypeError occurred while creating slice: {e}")
        raise
    except ValueError as e:
        print(f"ValueError occurred while creating slice: {e}")
        raise

def create_safe_slice(arg: Union[int, Tuple[int, ...], slice]) -> slice:
    """
    Creates a slice object based on the input argument.

    Args:
        arg (int, tuple, slice): The argument for creating the slice. It can be an integer, 
                                 a tuple with slice parameters, or a slice object itself.

    Returns:
        slice: A slice object created based on the provided argument.
    """
    try:
        if isinstance(arg, slice):
            return arg
        elif isinstance(arg, tuple):
            return slice(*arg)
        elif isinstance(arg, int):
            return slice(arg, arg + 1)
    except TypeError as e:
        print(f"TypeError occurred while creating slice: {e}")
        raise
    except ValueError as e:
        print(f"ValueError occurred while creating slice: {e}")
        raise

def generic_slice(array: np.ndarray, slice_params: Union[Tuple[Union[int, Tuple[int, ...], slice], ...], Union[int, Tuple[int, ...], slice]]) -> np.ndarray:
    """
    Slices a NumPy array based on a list of slice parameters for each dimension.

    Args:
        array (np.ndarray): The array to be sliced.
        slice_params (list): A list where each item is either an integer, a tuple with 
                             slice parameters, or a slice object.

    Returns:
        ndarray: The sliced array.
    """
    if not isinstance(slice_params, tuple):
        slice_params = (slice_params,)
    slices = tuple(create_safe_slice(param) for param in slice_params)
    return array.__getitem__(slices)

def validate_slice(slice_obj: Tuple[slice], target_array: np.ndarray) -> bool:
    """
    Validates if the given slice object is applicable to the target ndarray.

    Args:
        slice_obj (Tuple[slice]): A tuple containing slice objects for each dimension.
        target_array (np.ndarray): The array to be sliced.

    Returns:
        bool: True if the slice is valid for the given array, False otherwise.
    """
    if len(slice_obj) != target_array.ndim:
        return False

    for sl, size in zip(slice_obj, target_array.shape):
        # Check if slice start and stop are within the dimension size
        start, stop, _ = sl.indices(size)
        if not (0 <= start < size and (0 <= stop <= size or stop == -1)):
            return False
    return True
