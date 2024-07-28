# FJML
<img src="media/FJML_LOGO.png">

### FJML is a JSON based markup language which translates JSON files into Flet UI for web, mobile and desktop applications.


# Example:

```json title="ui.json"
{
    "Header":{
        "program_name":"Example"
    },
    "Controls":[
        {
            "var_name":"msg",
            "control_type":"Text",
            "settings":{
                "value":"Hello World",
                "size":20,
                "color":{"code_refs":"colors", "attr":"green"},
                "weight":{
                    "control_type":"FontWeight",
                    "attr":"W_700"
                }
            }
        },
        {
            "var_name":"msg_display",
            "control_type":"Container",
            "settings":{
                "content":{"refs":"msg"},
                "alignment":{"control_type":"alignment.center"},
                "border_radius":10,
                "padding":{
                    "control_type":"padding.symmetric",
                    "settings":{"horizontal":10, "vertical":8}
                },
                "width":200,
                "ink":true,
                "ink_color":{"code_refs":"colors", "attr":"grey"}
            }
        }
    ],
    "UI":[
        {
            "route":"/",
            "settings":{
                "controls":[
                    {"refs":"msg_display"}
                ],
                "horizontal_alignment":{"code_refs":"cross_align"},
                "vertical_alignment":{"code_refs":"main_align"}
            }
        }
    ]
}
```


```python title="func.py"
from fjml import data_types as dt
import flet as ft


class Colors:
    green: str = ft.colors.GREEN_600
    grey: str = ft.colors.GREY_200


class Actions(dt.EventContainer):

    def _page_setup(self):
        ...
    
    def _imports(self):
        self.colors: Colors = Colors()
        self.cross_align: str = ft.CrossAxisAlignment.CENTER
        self.main_align: str = ft.MainAxisAlignment.CENTER

```

```python title="main.py"
from fjml import load_program, Compiler, data_types as dt
from path.to.program import Actions
import flet as ft

class Paths:
    PROGRAM: str = "path\\to\\program_folder"
    COMPILED: str = "path\\to\\compiled_program\\compiled.fjml"

class App:

    def __init__(self, compile_run: bool = False) -> None:
        if compile_run:
            compiler: Compiler = Compiler(Paths.PROGRAM, Paths.COMPILED)
            compiler.compile()
        
    async def run(self, page: ft.Page):
        page = load_program(Paths.COMPILED, Actions)
        page.go("/")
    

if __name__ == "__main__":
    app: App = App(compile_run=True)
    ft.app(target=app.run)
```


## Python Integration

FJML allows the use of python code to perform actions such as API calls, function calls, etc. via the `EventContainer` Abstract Base Class.

- The main format of the Actions class which inherits from the `EventContainer` looks like this:
    ```python
    from fjml.data_types import EventContainer

    class Actions(EventContainer):

        def _page_setup(self):
            '''
            a custom page setup function to initialize your page object with data
            '''
        
        def _imports(self):
            '''
            an import function used to run operations outside of the page before rendering the UI
            '''
        
        #you can then add custom functions to be used throughout the FJML code
    ```


`EventContainer` also includes multiple built-in helper classes and functions to help create programs

- ### `EventContainer` methods and classes
   - ### **client_storage**:
        #### See [Flet Page Docs](https://flet.dev/docs/cookbook/client-storage)

   ---

   - ### **session**:
        #### See [Flet Page Docs](https://flet.dev/docs/cookbook/session-storage)

   ---

   - ### **update**:
        #### equivalent to `ft.Page.update`

   ---

   - ### **page**:
        #### See [Flet Page Docs](https://flet.dev/docs/controls/page).

   ---

   - ### **dict_to_control**:
       | Name                | Attributes                | Return           | Description                                                           |
       | ------------------- | ------------------------- | ---------------- | --------------------------------------------------------------------- |
       | **dict_to_control** | `control: dt.ControlDict` | `dt.ControlType` | Allows creating controls using FJML syntax inside the `EventContainer`. |

       - #### Example Usage:

           ```python
           
           class Actions(dt.EventContainer):

               def make_control(self) -> ft.Control:
                   return self.dict_to_control({
                       "control_type":"Container",
                       "settings":{
                           "alignment":{"control_type":"alignment.center"},
                           "content":{
                               "control_type":"Text",
                               "settings":{
                                   "value":"Hello World",
                                   "size":18
                               }
                           }
                       }
                   })
           ```

   ---

   - ### **group_assign**:
       | Name             | Attributes                                     | Return | Description                                               |
       | ---------------- | ---------------------------------------------- | ------ | --------------------------------------------------------- |
       | **group_assign** | `obj: Any', 'attribute_map: Mapping[str, Any]` | `None` | allows assigning multiple attributes to an object at once |

       - #### Example Usage:

           ```python

           class Data:
               f_name: str
               l_name: str
               age: int
           
           class Actions(dt.EventContainer):

               def fill_data(self) -> Data:
                   data: Data = Data()
                   self.group_assign(
                       data,
                       {
                           "f_name":"John",
                           "l_name":"Doe",
                           "age":21
                       }
                   )
                   return data
           ```

    ---

   - ### **eval_locals**:
       #### This class's main use is to add or delete locals from the evil statement's locals parameter.
       | Methods         | Attributes                | Return              | Description                                                       |
       | --------------- | ------------------------- | ------------------- | ----------------------------------------------------------------- |
       | **add**         | `name: str`, `obj: Any`   | `None`              | adds an object to the eval statement's locals                      |
       | **delete**      | `name: str`               | `None`              | deletes an object from the eval statement's locals                 |
       | **mass_add**    | `data: Mapping[str, Any]` | `None`              | adds multiple objects to the eval statement's locals               |
       | **mass_delete** | `data: Sequence[str]`     | `None`              | deletes multiple objects from the eval statement's locals          |
       | **data**        | `None`                    | `Mapping[str, Any]` | returns a copy of all preset locals in the eval statement's locals |

   ---

   - ### **object_bucket**:

       | Methods           | Attributes                            | Return | Description                                                                                             |
       | ----------------- | ------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------- |
       | **set_object**    | `name: str`, `obj: AnyCallable`       | `None` | adds any callable object to the bucket, so it can be called inside the UI code                       |
       | **call_object**   | `name: str`, `kwargs: dict[str, Any]` | `Any`  | calls the object with the necessary key word arguments. (used when object is called within the UI code) |
       | **delete_object** | `name: str`                           | `None` | deletes the object from the bucket                                                                      |

       #### This class's main use is to register objects for use in FJML code via the "**call**" designator:
       * ⠀
           ```json
           {
               "call":"get_text",
               "settings":{
                   "index":1
               }
           }
           ```
       
       #### If an object is not registered it can not be called but can only be referenced using a **code_refs** or the **func** designators.

   ---

   - ### **property_bucket**:
       | Methods      | Attributes                                    | Return | Description                                                                                                                                                        |
       | ------------ | --------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
       | **add**      | `name: str`, `obj: Any`                       | `None` | adds a property to be used as a `code_refs` inside the UI code                                                                                                     |
       | **contains** | `name: str`                                   | `bool` | used to check if a name is registered as property                                                                                                                  |
       | **call**     | `name: str`, `operation: str`, `set_val: Any` | `None` | Uses the property operations (set, get, del) to either set an object using the set_val parameter, get by just giving the name or deletion using the del operation. |

       #### This class's main use is to register python functions as properties to be used as **code_refs**

   ---

   - ### **setup_functions**:
       #### This class's main use is to register functions to be called to set up what ever API, environment, etc. when the UI starts up.
       | Methods            | Attributes                                        | Return | Description                            |
       | ------------------ | ------------------------------------------------- | ------ | -------------------------------------- |
       | **add_func**       | `func: Callable`, `parameters: Sequence[Any]`     | `None` | adds a function to the class           |
       | **mass_add_func**  | `items: Sequence[tuple[Callable, Sequence[Any]]]` | `None` | adds multiple functions to the class   |
       | **call_functions** | `None`                                            | `None` | calls all functions added to the class |

   ---

   - ### **style_sheet**:
       #### this class is used primarily for retrieving styles set inside the style sheet. This is mainly used in the "**_unpack**" designator via the `{"styling":"xyz"}` mapping value.
       | Methods       | Attributes  | Return        | Description                               |
       | ------------- | ----------- | ------------- | ----------------------------------------- |
       | **get_style** | `path: str` | `dt.JsonDict` | gets the style from a style sheet by name |

   ---

   - ### **view_operations**:
        #### This class is used to generate and register Flet views. Its main use is in the Flet's `Page.on_route_change` event.
        | Methods       | Attributes                                             | Return    | Description                                                 |
        | ------------- | ------------------------------------------------------ | --------- | ----------------------------------------------------------- |
        | **set_view**  | `route_name: str`, `view_settings: dt.ControlSettings` | `None`    | adds a `UIViews` to the compiled_model UI mapping attribute |
        | **add_view**  | `view: ft.View`                                        | `None`    | adds a Flet view control to the page views                  |
        | **make_view** | `view_model: UIViews`                                  | `ft.View` | generates a Flet view control from a `UIViews` type         |


## UI Format

### Main UI File:

```json
{
    "Header":{
        //Used to declare certain values
    },
    "Imports":[
        // Used to import controls from other files
    ],
    "Controls":[
        // Used to assign controls to variables
    ],
    "UI":[
        // Used to define route views
    ]
}
```

This format separates the header data, imports, controls and display UI.

- #### Header:
    Headers is primarily map based and thus requires one to use keys and values unlike the list based forms like the rest are. 
    The keys in this block consists of:
    
    - #### **import_folder**:
        | Value Type | Example   |
        | ---------- | --------- |
        | `str`      | `"extra"` |

        stores the name of the folder which contains the FJML imports
    
    - #### **program_name**:
        | Value Type | Example         |
        | ---------- | --------------- |
        | `str`      | `"Hello World"` |

        stores the name of the program

    - #### **style_sheet_name**:
        | Value Type | Example         |
        | ---------- | --------------- |
        | `str`      | `"style_sheet"` |
    
        Stores the name of the FJML style sheet.
        
    - #### **action_import**:
        | Value Type    | Example                          |
        | ------------- | -------------------------------- |
        | `dt.JsonDict` | `{"from":"...", "import":"..."}` |

        This dictionary imports the action class using the format:
        | Key        | Value Type | Example               |
        | ---------- | ---------- | --------------------- |
        | **from**   | `str`      | `".import_path.func"` |
        | **import** | `str`      | `"Action"`            |

        full example:
        ```json
        {
            "action_import":{
                "from":".import_path.func",
                "import":"Action"
            }
        }
        ```

        The `action_import` key's value is equivalent to: 
        - 
        ```python
        from .import_path.func import Action
        ```

        The import statement is run as if it was run in your main file.

    - #### **extensions**:
        | Value Type              | Example                                                |
        | ----------------------- | ------------------------------------------------------ |
        | `Sequence[dt.JsonDict]` | `[{"from":"...", "import":"...", "using":"..."}, ...]` |
        
        The value of this key consists of using a sequence of dictionaries which help import multiple controls at once:
        | Key        | Value Type                  | Example                                       |
        | ---------- | --------------------------- | --------------------------------------------- |
        | **from**   | `str`                       | `.custom_controls`                            |
        | **import** | `Union[str, Sequence[str]]` | `"CustomBtn"` or `["CustomBtn", "CustomTxt"]` |
        | **using**  | `Optional[str]`             | `"CC"`                                        |

        full example:
        ```json
        {
            "extensions":[
                {
                    "from":".custom_controls",
                    "import":["CustomBtn", "CustomTxt"],
                    "using":"CC"
                }
            ]
        }
        ```

        Using extension imports like this is equivalent to:
        - With the `using` key:
            - 
            ```python
                from . import custom_controls as CC
                from CC import CustomBtn, CustomTxt
            ```

            The use of these controls in FJML code will now have to use controls like so: `CC.CustomBtn`
        - Without the `using` key:
            - 
            ```python
                from .custom_controls import CustomBtn, CustomTxt
            ```

- #### Imports:
    Imports are called using the file name of the UI file defined inside the import folder defined by the key `"source"`. If the import folder includes different folders the use of the key `"folder"` can be used to indicate the specific folder inside the main import folder where you want to import from. e.g:
        - `{"source:"container_ui"}`
        - `{source:["user_ui", "admin_ui"], "folder":"person_ui_folder"}`

- #### Controls:
    controls can be named using the `"var_name"` key and then can be called and used in the python `"Action"` class using `"self.name_text"` or in another control using a dictionary using the `"refs"` key and the control name as its value. e.g: `{"refs":"name_text"}`
    Format example:
    ```json
    {
        "var_name":"foo",
        "control_type":"imported/registered control name",
        "settings":{
            ...
        }
    }
    ```

- #### UI:
    The UI section is used to define the route views used by you program.
    These views use the format of:
    ```json
    {
        "route":"/Home",
        "settings":{
            //any view settings needed. P.S. the route parameter will always be ignored if set in the settings block.
        }
    }
    ```
    and are contained in a Sequence

### Imported UI File:

With imports the JSON structure is similar except that it only has the `"Controls"` container. Using controls from other files is still possible once all dependencies are also imported into the main file. 

Imported file format:

```json
{
    "Controls":[]
}
```

### Style Sheet File:

With style sheets you are able to create styles for use later in your program. You are able to section off your styles by names and sub-names and thus call them using the format `{name}.{sub_name}.{sub_sub_name}...`. This format can go on forever if needed but can increase rendering time of your program if you go too deep.

Style sheet Format:
```json
{
    "name_1":{
        "sub_name":{
            "height":200,
            "width":500
        }
    },
    "name_2":{
        "sub_name":{
            "height":200,
            "width":500
        }
    }
}
```
styles can be used by then adding the `"_unpack"` attribute inside the control's `"settings"` dictionary with the dictionary formats:
- `{"styles":"{name}.{sub-name}"}`
- or `{"styles":"{name}.{sub-name} {name1}.{sub_name}"}` if multiple styles are needed


## Other FJML UI features include
- ### Calling functions and objects: 
    ```python
    class Action(EventContainer):

        def _imports(self) -> None:
            #register callable object
            self.object_bucket.set_object("calc_width", self.calc_width)
        
        def calc_width(self, height: int) -> int:
            return height*2
    
    ```
    ```json
    // call object
    {
        "control_type":"Container",
        "settings":{
            "width":{
                "call":"calc_width",
                "settings":{
                    "height":200
                }
            }
        }
    }
    
    ```
- ### UI loops:
    ```json
    {
        "control_type":"Column",
        "settings":{
            "controls":{
                "control_type":"loop",
                "depth":1,
                "iterator":[1,2,3,4,5],
                "control":{
                    "control_type":"Text",
                    "settings":{
                        "value":{
                            "control_type":"loop_index", 
                            "idx":[0]
                        }
                    }
                }
            }
        }
    }
    
    ```

- ### Adding control to variables:
    ```json
    {
        "var_name":"name", //<- Here
        "control_type":"Text",
        "settings":{
            "value":"John Doe",
            "size":18
        }
    }
    ```
    this can be accessed inside the Actions class using `self.name` and if control is defined as `self.name` inside Actions it can be called in FJML using `{"refs":"name"}`

- ### Using variables:

    Allows the use of FJML variables to be referenced in the same file or else where without the need for constant importing

    #### control variables:
    
    ```json
    {
        "var_name":"name", //<- Here
        "control_type":"Text",
        "settings":{
            "value":"John Doe",
            "size":18
        }
    }
    {
        "var_name":"text_container",
        "control_type":"Container",
        "settings":{
            "content":{"refs":"name"},
            "padding":6
        }
    }
    ```

    #### code variables:

    Allows the variables defined in python code to be accessed and used inside FJML code

    ```python
    class Actions(EventContainer):

        def _imports(self) -> None:
            self.text_size: int = 16
    ```

    ```json
    {
        "var_name":"name", //<- Here
        "control_type":"Text",
        "settings":{
            "value":"John Doe",
            "size":{"code_refs":"text_size"}
        }
    }
    ```

    #### Attribute and index calling

    The `idx` key works for both dictionaries and index based sequences.

    ```json
    {
        "var_name":"name", 
        "control_type":"Text",
        "settings":{
            "value":"John Doe",
            "size":18
        }
    }
    {
        "var_name":"get_display_name",
        "control_type":"Text",
        "settings":{
            "value":{
                "refs":"name",
                "attr":"value"
            },
            "size":18
        }
    }
    ```
    
    - #### Group chains:
    
        ```python
        
        class TextSizes:
            data: list[Union[dict[str, int], int]] = [18, {"name":16}]
        
        
        class Actions(EventContainer):
            def _imports(self) -> None:
                self.text_sizes: TextSizes = TextSizes()

        ```

        ```json
        {
            "var_name":"name",
            "control_type":"Text",
            "settings":{
                "value":"John Doe",
                "size":{
                    "code_refs":"text_sizes",
                    "group":[
                        {"attr":"data"},
                        {"idx":1},
                        {"idx":"name"}
                    ]
                }
            }
        }
        ```
- ### Action Class:
    In order to link your action class to FJML code you must import the in the `Header` container using the key, `action_import`.
    - #### Example:

        ```json
        {
            "Header":{
                "action_import":{
                    "import":"Actions",
                    "from":".ui_test_program.func"
                }
            },
            "Imports":[...],
            "Controls":[...],
            "UI":[...]
        }
        ```

    All action imports must exist in an importable path and be written as if it was run in the `main.py` file.


- ### Custom Controls:
    FJML allows you multiple ways to define and add custom controls to your project.
    This is done by using the `"extensions"` key inside the `"Header"`:

    ```json
    {
        "Header":{
            "extensions":[
                {
                    "using":"fm",
                    "import":["Buttons", "Switches"],
                    "from":"flet_material"
                }
            ]
        },
        "Imports":[...],
        "Controls":[
            {
                "var_name":"switch",
                "control_type":"fm.Switches",
                "settings":{}
            }
        ],
        "UI":[...]
    }
    ```

    All imports must already be installed or exist in an importable path.
<br></br>
<br></br>

- # **Running the app**
   
    ```python title="main.py"
    from fjml import load_program, Compiler, data_types as dt
    import flet as ft

    class Paths:
        PROGRAM: str = "path\\to\\program_folder"
        COMPILED:str = "path\\to\\compiled_program\\compiled.fjml"

    class App:

        def __init__(self, compile_run: bool = False) -> None:
            if not compile_run:
                return
                 
            compiler: Compiler = Compiler(Paths.PROGRAM, Paths.COMPILED)
            compiler.compile()
            
        async def run(self, page: ft.Page):
            page = load_program(Paths.COMPILED, page)
            page.go("/")

    if __name__ == "__main__":
        app: App = App(compile_run=True)
        ft.app(target=app.run)
    ```
