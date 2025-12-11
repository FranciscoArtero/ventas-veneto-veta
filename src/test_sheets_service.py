import pytest
from unittest.mock import MagicMock
from src.services.sheets import SheetsService
from src.models import StockItem
import gspread

@pytest.fixture
def mock_gspread_client(mocker):
    """Fixture que mockea el cliente de gspread."""
    # Mockear la autenticación
    mocker.patch('gspread.service_account', return_value=MagicMock())

    # Mockear el cliente, spreadsheet y worksheet
    mock_client = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_worksheet = MagicMock()

    mock_client.open.return_value = mock_spreadsheet
    mock_spreadsheet.worksheet.return_value = mock_worksheet

    # Simular que gspread.service_account() devuelve nuestro cliente mockeado
    mocker.patch('src.services.sheets.gspread.service_account', return_value=mock_client)
    
    return mock_client, mock_spreadsheet, mock_worksheet

def test_leer_stock_success(mock_gspread_client):
    """Prueba que leer_stock procesa correctamente los datos."""
    _, _, mock_worksheet = mock_gspread_client

    # Datos simulados que devolvería get_all_records()
    mock_records = [
        {'id': 1, 'codigo': 'A001', 'nombre': 'Producto 1', 'categoria': 'Cat A', 'cantidad': 10, 'precio_unitario': 100.0, 'stock_minimo': 5, 'ultima_actualizacion': '2023-10-27T10:00:00+00:00'},
        {'id': 2, 'codigo': 'A002', 'nombre': 'Producto 2', 'categoria': 'Cat B', 'cantidad': 20, 'precio_unitario': 150.0, 'stock_minimo': 5, 'ultima_actualizacion': '2023-10-27T11:00:00+00:00'}
    ]
    mock_worksheet.get_all_records.return_value = mock_records

    # Inyectamos una ruta de credenciales falsa para que no falle el constructor
    service = SheetsService(credentials_path='fake_creds.json')
    items = service.leer_stock('fake_sheet')

    assert len(items) == 2
    assert isinstance(items[0], StockItem)
    assert items[0].nombre == "Producto 1"
    assert items[1].cantidad == 20

def test_leer_stock_with_bad_data(mock_gspread_client):
    """Prueba que leer_stock omite registros con datos incorrectos."""
    _, _, mock_worksheet = mock_gspread_client

    # Un registro bueno y uno malo (sin 'nombre')
    mock_records = [
        {'id': 1, 'codigo': 'A001', 'nombre': 'Producto 1', 'categoria': 'Cat A', 'cantidad': 10, 'precio_unitario': 100.0, 'stock_minimo': 5, 'ultima_actualizacion': '2023-10-27T10:00:00+00:00'},
        {'id': 2, 'codigo': 'A002', 'categoria': 'Cat B', 'cantidad': 20} # Falta 'nombre'
    ]
    mock_worksheet.get_all_records.return_value = mock_records

    service = SheetsService(credentials_path='fake_creds.json')
    items = service.leer_stock('fake_sheet')

    # Solo el registro bueno debería ser procesado
    assert len(items) == 1
    assert items[0].id == 1