import arrow
import requests
import pandas as pd

timezone = 'Canada/Mountain'


def fetch_production(country_code='CA-AB', session=None):
    """Requests the last known production mix (in MW) of a given country

    Arguments:
    country_code (optional) -- used in case a parser is able to fetch multiple countries
    session (optional)      -- request session passed in order to re-use an existing session

    Return:
    A dictionary in the form:
    {
      'countryCode': 'FR',
      'datetime': '2017-01-01T00:00:00Z',
      'production': {
          'biomass': 0.0,
          'coal': 0.0,
          'gas': 0.0,
          'hydro': 0.0,
          'nuclear': null,
          'oil': 0.0,
          'solar': 0.0,
          'wind': 0.0,
          'geothermal': 0.0,
          'unknown': 0.0
      },
      'storage': {
          'hydro': -10.0,
      },
      'source': 'mysource.com'
    }
    """
    r = session or requests.session()
    url = 'http://ets.aeso.ca/ets_web/ip/Market/Reports/CSDReportServlet'
    response = r.get(url)
    df_generations = pd.read_html(response.text, match='GENERATION', skiprows=1, index_col=0, header=0)
    total_net_generation = df_generations[1]['TNG']
    maximum_capability = df_generations[1]['MC']
    
    return {
        'datetime': arrow.now(tz=timezone).floor('minute').datetime,
        'countryCode': country_code,
        'production': {
            'coal': total_net_generation['COAL'],
            'gas': total_net_generation['GAS'],
            'hydro': total_net_generation['HYDRO'],
            'wind': total_net_generation['WIND'],
            'unknown': total_net_generation['OTHER']
        },
        'capacity': {
            'coal': maximum_capability['COAL'],
            'gas': maximum_capability['GAS'],
            'hydro': maximum_capability['HYDRO'],
            'wind': maximum_capability['WIND'],
            'unknown': maximum_capability['OTHER']
        },
        'source': 'ets.aeso.ca',
    }


def fetch_price(country_code='CA-AB', session=None):
    """Requests the last known power price of a given country

    Arguments:
    country_code (optional) -- used in case a parser is able to fetch multiple countries
    session (optional)      -- request session passed in order to re-use an existing session

    Return:
    A dictionary in the form:
    {
      'countryCode': 'FR',
      'currency': EUR,
      'datetime': '2017-01-01T00:00:00Z',
      'price': 0.0,
      'source': 'mysource.com'
    }
    """

    r = session or requests.session()
    url = 'http://ets.aeso.ca/ets_web/ip/Market/Reports/SMPriceReportServlet?contentType=html/'
    response = r.get(url)
    df_prices = pd.read_html(response.text, match='Price', index_col=0, header=0)
    prices = df_prices[1]

    data = {}

    for rowIndex, row in prices.iterrows():
        price = row['Price ($)']
        if (isfloat(price)):
            hours = int(rowIndex.split(' ')[1]) - 1
            data[rowIndex] = {
                'datetime': arrow.get(rowIndex, 'MM/DD/YYYY').replace(hours=hours, tzinfo=timezone).datetime,
                'countryCode': country_code,
                'currency': 'CAD',
                'source': 'ets.aeso.ca',
                'price': float(price),
            }

    return [data[k] for k in sorted(data.keys())]


def fetch_exchange(country_code1='CA-AB', country_code2='CA-BC', session=None):
    """Requests the last known power exchange (in MW) between two countries

    Arguments:
    country_code (optional) -- used in case a parser is able to fetch multiple countries
    session (optional)      -- request session passed in order to re-use an existing session

    Return:
    A dictionary in the form:
    {
      'sortedCountryCodes': 'DK->NO',
      'datetime': '2017-01-01T00:00:00Z',
      'netFlow': 0.0,
      'source': 'mysource.com'
    }
    """

    r = session or requests.session()
    url = 'http://ets.aeso.ca/ets_web/ip/Market/Reports/CSDReportServlet'
    response = r.get(url)
    df_exchanges = pd.read_html(response.text, match='INTERCHANGE', skiprows=0, index_col=0)
    
    flows = {
        'CA-AB->CA-BC': df_exchanges[1][1]['British Columbia'],
        'CA-AB->CA-SK': df_exchanges[1][1]['Saskatchewan'],
        'CA-AB->US': df_exchanges[1][1]['Montana']
    }
    sortedCountryCodes = '->'.join(sorted([country_code1, country_code2]))
    if sortedCountryCodes not in flows:
        raise NotImplementedError('This exchange pair is not implemented')
    
    return {
        'datetime': arrow.now(tz=timezone).datetime,
        'sortedCountryCodes': sortedCountryCodes,
        'netFlow': float(flows[sortedCountryCodes]),
        'source': 'ets.aeso.ca'
    }


def isfloat(value):
    try:
      float(value)
      return True
    except ValueError:
      return False


if __name__ == '__main__':
    """Main method, never used by the Electricity Map backend, but handy for testing."""

    print 'fetch_production() ->'
    print fetch_production()
    print 'fetch_price() ->'
    print fetch_price()
    print 'fetch_exchange() ->'
    print fetch_exchange()
