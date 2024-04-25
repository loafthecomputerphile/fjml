from docxtpl import DocxTemplate
import os.path
import pandas as pd
import struct
from dataclasses import dataclass, field
from pathvalidate import validate_filepath
from docx2pdf import convert
from typing import (
    Any, 
    NoReturn, 
    Callable, 
    Optional, 
    Union, 
    TypeAlias, 
    Mapping, 
    Literal,
    Final
)

StringDictType: TypeAlias = Union[str, dict[str, str]]
ProcessorFunc: TypeAlias = Union[Callable[..., StringDictType], str, None]
Args: TypeAlias = tuple[str, ...]
Kwargs: TypeAlias = dict[str, Any]
TYPES: Final[list[str]] = ["integer", "string", "float", "bool"]

@dataclass
class Preprocessor:
    name: str
    function: Callable
    params_spec: dict[str, str]
    
    def __post_init__(self) -> NoReturn:
        self.func_name: str = self.function.__name__


def groupby(data: pd.DataFrame, column: str) -> dict[str, StringDictType]:
    
    grouped_data: pd.DataFrame = data.groupby(column).apply(lambda x: x[:])
    indexes: list[str] = list(grouped_data.index.get_level_values(0))
    
    group_func: Callable[[str], tuple[str, dict]] = (
        lambda x: (x, grouped_data.loc[x].to_dict("index"))
    )
    
    mapping: Mapping = map(
        group_func, indexes
    )
    
    return dict(mapping)

def every_n_row(data: pd.DataFrame, rows: int) -> dict[str, dict[str, Any]]:
    split_func: Callable[[int], int] = (
        lambda idx: idx // rows
    )
    
    grouped_data = enumerate(data.groupby(split_func))
    
    group_func: Callable[[tuple[Any, Any]], tuple[str, dict]] = (
        lambda data: (data[0]+1, data[1].to_dict("index"))
    )
    
    mapping: Mapping = map(
        group_func, grouped_data
    )
    
    return dict(mapping)


def plain_copy(data: pd.DataFrame) -> dict[str, dict[str, Any]]:
    return data.to_dict("index")


def is_docx(file: str) -> bool:
    with open(file, 'rb') as stream:
        buffer = stream.read()
        
    fingerprint = []
    if len(buffer) > 4:
        for i in range(4):
            byte = struct.unpack_from("<B", buffer, i)[0]
            fingerprint.append("{0:x}".format(byte).upper())
    else:
        return False
    return ' '.join(fingerprint) == "50 4B 03 04"

class WordTemplateWriter:
    
    __slots__ = ["document_path", "template", "template_inputs", "constants", "added_funcs"]
    
    TYPES: list[str] = TYPES
    
    preprocessor_functions: list[Preprocessor] = [
        Preprocessor("Group By Column", groupby, {"column":"string"}),
        Preprocessor("Plain Copy", plain_copy, {}),
        Preprocessor("Groups of Rows", every_n_row, {"rows":"integer"})
    ]
    
    def __init__(self, document_path: str, constants: Optional[dict[str, Any]] = None) -> NoReturn:
        self.template_inputs: dict[str, StringDictType] = dict()
        self.added_funcs: list[str] = []
        if constants:
            self.add_data_group(constants)
        self.document_path: str = document_path
        self.template: DocxTemplate = DocxTemplate(self.document_path)
    
    def add_preprocessor(preprocessors: list[Preprocessor]) -> NoReturn:
        self.preprocessor_functions.extend(preprocessors)
    
    def add_data(self, key: str, data: Any, preprocessor: str = None, processor_kwargs: Kwargs = {}) -> NoReturn:
        processor: Preprocessor = None
        
        if isinstance(preprocessor, str):
            processor = self.preprocessor_functions[[p.func_name for p in self.preprocessor_functions].index(preprocessor)]
        
        if not processor:
            self.template_inputs[key] = data
            return
        
        self.template_inputs[key] = processor.function(data, **processor_kwargs)
        #print(self.template_inputs[key])
        self.added_funcs.append(key)
    
    def run_funcs(self) -> NoReturn:
        key: str
        
        for key in self.added_funcs:
            self.template_inputs[key] = self.template_inputs[key]()
    
    def add_data_group(self, data: dict[str, StringDictType]) -> NoReturn:
        self.template_inputs.update(data)
    
    def implement_changes(self) -> NoReturn:
        #self.run_funcs()
        self.template.render(self.template_inputs)
    
    def save_file(self, save_path: str) -> NoReturn:
        self.template.save(save_path)

    def reset(self) -> NoReturn:
        self.template_inputs = dict()
        self.added_funcs = []
        self.document_path = ""
    


class WordToPdf:
    
    def convert_folder(self, folder_path: str, output_path: str = None) -> NoReturn:
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Path {folder_path} doesnt exist") 
        
        if not os.path.isdir(folder_path):
            raise Error(f"folder_path, {folder_path}, is not a path")
        
        if output_path and not validate_filepath(output_path): 
            raise Error(f"output_path, {output_path}, is not a path")
        
        convert(folder_path, output_path)
    
    def convert_file(self, document_path: str, output_path: str = None) -> NoReturn:
        if not os.path.exists(document_path):
            raise FileNotFoundError(f"Path {document_path} doesnt exist")
        
        if not os.path.isfile(document_path):
            raise Error(f"document_path, {document_path}, is not a file")
        
        if not is_docx(document_path):
            raise Error(f"document from path, {document_path}, is not a docx file")
        
        convert(document_path, output_path)