# FJML
<img src="media/FJML_LOGO.png">

### FJML is a Json based markup language which translates json files into Flet UI for web, mobile and desktop applications.


# Example:

```json
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
                    "control_type":"padding.symmentric",
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


```python
from fjml import data_types as dt
import flet as ft


class Colors:
    green: str = ft.colors.GREEN_600
    grey: str = ft.colors.GREY_200


class Actions(dt.EventContainer):

    def _page_setup(self):
        '''
        a custom page setup function if needed before rendering the UI and adding it to the page
        '''
    
    def _imports(self):
        self.colors: Colors = Colors()
        self.cross_align: str = ft.CrossAxisAlignment.CENTER
        self.main_align: str = ft.MainAxisAlignment.CENTER

    #you can then add custom functions to be used throughout the fjml code
```



```python title="main.py"
    from fjml import load_program, Compiler, data_types as dt
    from path.to.program import Actions
    import enum
    import flet as ft

    class Paths(enum.StrEnum):
        PROGRAM: str = "path\\to\\program"
        COMPILED: str = "path\\to\\compiled_program\\compiled.fjml"

    class App:

        def __init__(self, compile_run: bool = False) -> None:
            if not compile_run:
                compiler: Compiler = Compiler(
                    dt.ParamGenerator(
                        program_path=Paths.PROGRAM
                        compile_path=Paths.COMPILED
                    )
                )
                compiler.compile()
            
        async def run(self, page: ft.Page):
            page = load_program(
                Paths.COMPILED, Actions, page
            )
            page.go("/")
         


    if __name__ == "__main__":
        app: App = App(compile=True)
        ft.app(target=app.run)
    ```


## Python Integration

Allows the use of python code to perform actions such as api calls, function calls, etc via the `EventContainer` Abstract Base Class 

`EventContainer` includes builtin helper classes and functions like:
- # EventContainer methods and classes


   - ### update:
       #### equivalent to `ft.Page.update`

   ---

   - ### page:
       #### See [Flet Page Docs](https://flet.dev/docs/controls/page).

   ---

   - ### dict_to_control:
       | Name      | Attributes        | Return        | Description         |
       | --------- | ----------------- | ------------- | ------------------- |
       | __dict_to_control__ | `control: dt.ControlDict` | `dt.ControlType` | Allows creating controls using fjml syntax inside the EventContainer. |

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
       | Name      | Attributes        | Return        | Description         |
       | --------- | ----------------- | ------------- | ------------------- |
       | __group_assign__ | `obj: Any', 'attribute_map: Mapping[str, Any]` | `None` | allows assigning multiple attributes to an object at once|

       - #### Example Usage:

           ```python

           class Data:
               fname: str
               lname: str
               age: int
           
           class Actions(dt.EventContainer):

               def fill_data(self) -> Data:
                   data: Data = Data()
                   self.group_assign(
                       data,
                       {
                           "fname":"John",
                           "lname":"Doe",
                           "age":21
                       }
                   )
                   return data
           ```

   ---

   - ### object_bucket:

       | Methods      | Attributes | Return       | Description
       | ----------- | ----------- | ----------- | ----------- |
       | __set_object__      | `name: str`, `obj: AnyCallable`  |`None`     | adds any callable object to the the bucket so it can be called inside the UI code|
       | __call_object__   | `name: str`, `kwargs: dict[str, Any]`       | `Any`         | calls the object with the necessary key word arguments. (used when object is called within the UI code)             |
       | __delete_object__   | `name: str`       | `None`         | deletes the object from the bucket             |

       #### This class's main use is to register objects for use in fjml code via the "__call__" designator:
       * ⠀
           ```json
           {
               "call":"get_text",
               "settings":{
                   "index":1
               }
           }
           ```
       
       #### if an object is not registered it can not be called but can only be referenced using a __code_refs__ or the __func__ designators.

   ---

   - ### property_bucket:
       | Methods      | Attributes | Return       | Description
       | ----------- | ----------- | ----------- | ----------- |
       | __add__      | `name: str`, `obj: Any`  |`None`     | adds a property to be used as a `code_refs` inside the UI code|
       | __contains__   | `name: str`       | `bool`         | used to check if a name is registeerd as property             |
       | __call__   | `name: str`, `operation: dt.PropertyLabel`, `set_val: PropertyLiteral`       | `None`         | Uses the property operations (set, get, del) to either set an object using the set_val parameter, get by just giving the name or deletion using the del operation.|

       #### This class's main use is to register python functions as properties to be used as **code_refs**

   ---

   - ### setup_functions:
       #### This class's main use is to register functions to be called to setup what ever api, environment, etc when the UI starts up.
       | Methods     | Attributes     | Return | Description |
       | ----------- | -------------- | ------ | ----------- |
       | __add_func__ | `func: Callable`, `parameters: Sequence[Any]` | None | adds a function to the class |
       | __mass_add_func__ | `items: Sequence[tuple[Callable, Sequence[Any]]]` | `None` | adds multiple functions to the class |
       | __call_functions__| `self` | `None` | calls all functions added to the class|

   ---

   - ### style_sheet:
       #### this class is used primarily for retrieving styles set inside the style sheet. This is mainly used in the "**unpack**" designator via the `{"styling":"xyz"}` mapping value.
       | Methods    | Attributes    | Return        | Description |
       | ---------- | ------------- | ------------- | ----------- |
       | __get_style__  | `path: str` | `dt.JsonDict` | gets the style from a style sheet by name       |

   ---

   - ### view_operations:
       This class is used to generate and register flet views. its main use is in the flet's `Page.on_route_change` event.
       | Methods | Attributes  | Return  | Description |
       | ------- | ----------- | ------- | ----------- |
       | __set_view__ | `route_name: str`, `view_settings: dt.ControlSettings` | `None`  | adds a `UIViews` to the compiled_model ui mapping attribute |
       | __add_view__ | `view: ft.View` | `None`  | adds a flet view control to the page views |
       | __make_view__       | `view_model: UIViews` | `ft.View` | generates a flet view control from a `UIViews` type  |

```python
from fjml.data_types import EventContainer

class Actions(EventContainer):

    def _page_setup(self):
        '''
        a custom page setup function if needed before rendering the UI and adding it to the page
        '''
    
    def _imports(self):
        '''
        an import function used to run operations outside of the page before rendering the UI and adding it to the page 
        '''
    

    #you can then add custom functions to be used throughout the fjml code
```

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

This format seperates the imports, controls and display ui.

- #### Header:
    Headers is a primarily Map based and thus requres one to use keys and values unlike the list based forms the rest are. This block defines the program's name, extra import folder name (for the Imports Section) and the style_sheet name.

- #### Imports:
    Imports are called using the file name of the ui file defined inside the import folder defined by the key `"source"`. if the import folder includes different folders the use of the key `"folder"` can be used to indicate the specific folder inside the main import folder where you want to import from. e.g:
        - `{"source:"container_ui"}`
        - `{source:["user_ui", "admin_ui"], "folder":"person_ui_folder"}`

- #### Controls:
    controls can be named using the `"var_name"` key and then can be called and used in the python `"Action"` class using `"self.name_text"` or in another control using a dictionary using the `"refs"` key and the control name as its value. e.g: `{"refs":"name_text"}`

- #### UI:
    The UI section is used to define the route views used by you program.
    these views use the format of:
    ```json
    {
        "route":"/Home",
        "settings":{
            //any view settings needed. P.S. the route parameter will always be ignored if set in the settings block.
        }
    }

    ```

### Imported UI File:

With imports the json structure is similiar except that it only has the `"Controls"` container.Using controls from other files is still possible once all dependencies are also imported into the main file. 

Imported file format:

```json
{
    "Controls":[]
}
```

### Style Sheet File:

With style sheets you are able to create styles for use later in your program. You are able to section off your styles by names and sub-names and thus call them using the format `{name}.{sub_name}.{sub_sub_name}...`.This format can go on forever if needed but can increase rendering time of your program if you go too deep.

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
styles can be used by then adding the `"unpack"` attribute inside the control's `"settings"` dictionary with the dictionary formats:
- `{"styles":"{name}.{sub-name}"}`
- or `{"styles":"{name}.{sub-name} {name1}.{sub_name}"}` if multiple styles are needed




## Other FJML UI features include
- ### Calling functions and objects: 
    ```python
    class Action(EventContainer):

        async def _imports(self) -> None:
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
    this can be accessed inside the Actions class using self.name and if control is defined as self.name inside Actions  it can be called in fjml using {"refs":"name"}

- ### Using variables:

    Allows the use of fjml variables to be referenced in the same file or else where without the need for constant importing

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

    Allows the variables defined in python code to be accessed and used inside fjml code

    ```python
    class Actions(EventContainer):

        async def _imports(self) -> None:
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

    #### Attriute and index calling:

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

- ### Custom Controls:
    Fjml allows you multiple ways to define and add custom controls to your project.
    This is done by using the `"extentions"` key inside the `"Header"`:

    ```json
    {
        "Header":{
            "extentions":[
                {
                    "using":"fm",
                    "import":["Buttons", "Switchs"],
                    "from":"flet_material"
                }
            ]
        },
        "Controls":[
            {
                "var_name":"switch",
                "control_type":"fm.Switchs",
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
   
   After this has been done you must add the list to the `ParamGenerator` class inside the `Compiler` class

    ```python title="main.py"
    from fjml import load_program, Compiler, data_types as dt
    from path.to.program import Actions
    import enum
    import flet as ft

    class Paths(enum.StrEnum):
        PROGRAM: str = "path\\to\\program"
        COMPILED: str = "path\\to\\compiled_program\\compiled.fjml"

    class App:

        def __init__(self, compile_run: bool = False) -> None:
            if not compile:
                return
                 
            compiler: Compiler = Compiler(
                dt.ParamGenerator(
                    program_path=Paths.PROGRAM
                    compile_path=Paths.COMPILED
                )
            )
            compiler.compile()
            
        async def run(self, page: ft.Page):
            page = load_program(
                Paths.COMPILED, Actions, page
            )
            page.go("/")
         


    if __name__ == "__main__":
        app: App = App(compile=True)
        ft.app(target=app.run)
    ```
