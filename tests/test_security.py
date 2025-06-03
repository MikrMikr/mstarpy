from mstarpy.security import Security

def test_security():
    security = Security("visa", exchange='XNYS')
    assert "Visa Inc Class A" == security.name
    assert "XNYS" == security.exchange
    assert "0P0000CPCP" == security.code