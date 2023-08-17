import requests

def get_error_count():
    response = requests.post(
            'https://apuestanext.com/apuestanext.com/aplicativo/accion/apis/error_count.php',
    )
    if(response.status_code != 200):
        return {}
    return response.json()[0]

def get_errors(caso):
    data = {
        "caso": caso,
    }
    response = requests.post(
        url='https://apuestanext.com/apuestanext.com/aplicativo/accion/apis/error_matilog.php',
        json=data
    )
    return response.json()
