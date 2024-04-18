# FJML
<img src="media/FJML_LOGO.png">

FJML is a Json based markup language which translates json objects into Flet UI for web, mobile and desktop applications.

### Python Integration

Allows the use of python code to perform actions such as api calls and code running via the EventContainer Abstract Base Class 

```python
from fjml.data_types import EventContainer

class Action(EventContainer):

    async def _page_setup(self):
        '''
        a custom page setup function if needed before rendering the UI and adding it to the page
        '''
    
    async def _imports(self):
        '''
        an import function used to run operations outside of the page before rendering the UI and adding it to the page 
        '''
    
    async def _on_close(self):
        '''
        a close function to clean up your code before closing the page
        '''

    #you can then add custom functions to be used throughout the fjml code
```

#### New custom UI features include
- Control Naming:
    ```json
    {
        "var_name":"field", // <- Here
        "control_type":"TextField",
        "settings":{
            "width":100
        }
    }
    ```
- Calling functions and objects: 
    ```python
    class Action(EventContainer):

        async def _imports(self) -> None:
            #register callable object
            self.set_object("calc_width", self.calc_width)
        
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
- UI loops:
    ```json
    {
        "control_type":"Column",
        "settings":{
            "controls":[
                {
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
            ]
        }
    }
    
    ```

- adding control to variables:
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
    this can be accessed inside the Actions class using self.name and if control is defined as self.name inside Actions  it can be called in fjml using {"ref":"name"}

- Parameter unpacking:
    ```json
    {
        "var_name":"textfield_params",
        "control_type":"ref",
        "settings":{
            "text_size":16,
            "height":40,
            "border_width":1.6,
            "border_color":"grey900",
            "content_padding":{
                "l":10,
                "r":10,
                "t":6,
                "b":6
            },
            "border_radius":10,
            "expand":2
        }
    },
    {
        "var_name":"field",
        "control_type":"TextField",
        "settings":{
            "unpack":{"ref":"textfield_params"}
        }
    }
    ```
- Use of Custom Controls:
    ```python title="main.py"
    from fjml import (
        ProgramLoader,
        data_types as dt
    )
    import flet as ft
    from ./path/to/actions import Actions

    CUSTOM_CONTROLS = [
        {
            "name":"CustomButton",
            "source":"my_controls",
            "attr":"CustomButton",
            "is_awaitable":False
        }
    ]

    async def main(page: ft.Page):
        ProgramLoader(
            dt.LoaderParameters(
                page=page,
                program_name="my program",
                imports_path="path/to/ui_imports/folder",
                custom_controls=CUSTOM_CONTROLS,
                methods=Actions,
                ui_code="path/to/ui.json"
            )
        )

        def view_pop(view):
            page.views.pop()
            top_view = page.views[-1]
            page.go(top_view.route)
        
        page.on_view_pop = view_pop
        
        page.go(page.route)

    if __name__ == "__main__":
        ft.app(target=main)
    ```
