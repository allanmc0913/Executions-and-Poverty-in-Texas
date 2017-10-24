#Running the code and generating the CSV file will take between 4-8 minutes (depending on the current API traffic)
#Allan Chen
#SI330 Final Project
#Winter 2017

from urllib.request import urlopen
from bs4 import BeautifulSoup
import csv
import re
import requests
import json

BASE_URL = 'https://www.tdcj.state.tx.us'

inmatelst = []

#Dictionary assignment for each of the 542 executed inmates
def gettabledata():

    #Connect to executed inmates webpage
    with urlopen('https://www.tdcj.state.tx.us/death_row/dr_executed_offenders.html') as response:
        soup = BeautifulSoup(response, 'html.parser')
        rows = soup.find('table').find_all('tr')
        #Deleting first list element as it contains HTML header information
        del rows[0]

        #Iterate through all table elements to assign initial dictionary values
        for tr in rows:
            tds = tr.find_all('td')
            inmatedict = {'Execution No.': int(tds[0].string.strip()),
                          'More Info URL': BASE_URL + tds[1].find('a').get('href'),
                          'Last Statement URL': BASE_URL + tds[2].find('a').get('href'),
                          'First Name': tds[4].string.strip(),
                          'Last Name': tds[3].string.strip(),
                          'TDCJ Number': int(tds[5].string.strip()),
                          'Execution Age': int(tds[6].string.strip()),
                          'Execution Date': tds[7].string.strip(),
                          'Race': tds[8].string.strip(),
                          'County': tds[9].string.strip(),
                          'DOB': None,
                          'Date Received': None,
                          'Age Received': None,
                          'Date of Offense': None,
                          'Age at Offense': None,
                          'Gender': None,
                          'Education Level': None,
                          'Hair Color': None,
                          'Weight': None,
                          'Eye Color': None,
                          'Native State': None,
                          'Last Statement': "Hello",
                          'Sentiment': None
                          }
            if "death_row" not in inmatedict['Last Statement URL']:
                reg = re.search(r'([\w./:]+)\.usdr([\w./]+)', inmatedict['Last Statement URL'])
                inmatedict['Last Statement URL'] = reg.group(1) + ".us/death_row/dr" + reg.group(2)
            if "death_row" not in inmatedict['More Info URL']:
                reg = re.search(r'([\w./:]+)\.usdr([\w./]+)', inmatedict['More Info URL'])
                inmatedict['More Info URL'] = reg.group(1) + ".us/death_row/dr" + reg.group(2)



            #Connect to Last Statement URL, find all <p> tags
            with urlopen(inmatedict['Last Statement URL']) as response2:
                soup2 = BeautifulSoup(response2, 'html.parser')
                div = soup2.find_all('p')

                #Iterate through each <p> tag in list, find <p> tag with header text "Last Statement:"
                #Invoke method .find_next_sibling() to get the Last Statement tag and text
                #Replace leading/trailing quotes before passing into API
                #Encode/Decode
                #Update dictionary
                for element in div:
                    if element.text.strip() == "Last Statement:":
                        before = element
                        laststatement = before.find_next_sibling().text.strip()
                        laststatement = laststatement.replace("“", "")
                        laststatement = laststatement.replace("”", "")
                        laststatement = laststatement.encode(encoding='utf-8')
                        laststatement = laststatement.decode(encoding='latin-1')
                        inmatedict['Last Statement'] = laststatement

            #Some links for more offender information aren't text that I can extract using BS, but rather JPEG images of the actual inmate record.
            #Using regex, if the url ends in JPEG, update dictionary keys with values of "N/A"
            imageurls = re.findall(r'.+[.jpg]$', inmatedict['More Info URL'])
            if len(imageurls) > 0:
                inmatedict['DOB'] = "N/A"
                inmatedict['Date Received'] = "N/A"
                inmatedict['Age Received'] = "N/A"
                inmatedict['Date of Offense'] = "N/A"
                inmatedict['Age at Offense'] = "N/A"
                inmatedict['Gender'] = "N/A"
                inmatedict['Education Level'] = "N/A"
                inmatedict['Hair Color'] = "N/A"
                inmatedict['Weight'] = "N/A"
                inmatedict['Eye Color'] = "N/A"
                inmatedict['Native State'] = "N/A"

            #If length is 0, it means that the more information URL does not end in JPEG, which means it is then in HTML format that I can use BS to scrape.
            #Connect to More Info URL, find all table elements
            #Try assigning values into dictionary after grabbing string and stripping
            #Use compiled regex to clean data to get just the integers for columns like Weight
            #Except clause accomodates when there is not HTML on the page
            if len(imageurls) == 0:
                with urlopen(inmatedict['More Info URL']) as response3:
                    soup3 = BeautifulSoup(response3, 'html.parser')
                    tds = soup3.find_all('td')
                    regex = re.compile(r'([0-9]+)')

                    try:
                        inmatedict['DOB'] = tds[6].string.strip()
                        inmatedict['Date Received'] = tds[8].string.strip()
                        inmatedict['Age Received'] = int(tds[10].string.strip())
                        education = tds[12].string.strip()
                        educationint = regex.findall(education)
                        inmatedict['Education Level'] = int(educationint[0])
                        inmatedict['Date of Offense'] = tds[14].string.strip()
                        inmatedict['Age at Offense'] = int(tds[17].string)
                        inmatedict['Gender'] = tds[26].string.strip()
                        inmatedict['Hair Color'] = tds[29].string.strip()
                        weight = tds[35].string.strip()
                        weightint = regex.findall(weight)
                        inmatedict['Weight'] = int(weightint[0])
                        inmatedict['Eye Color'] = tds[38].string.strip()
                        inmatedict['Native State'] = tds[44].string.strip()

                    except:
                        inmatedict['DOB'] = "N/A"
                        inmatedict['Date Received'] = "N/A"
                        inmatedict['Age Received'] = "N/A"
                        inmatedict['Education Level'] = "N/A"
                        inmatedict['Date of Offense'] = "N/A"
                        inmatedict['Age at Offense'] = "N/A"
                        inmatedict['Gender'] = "N/A"
                        inmatedict['Hair Color'] = "N/A"
                        inmatedict['Weight'] = "N/A"
                        inmatedict['Eye Color'] = "N/A"
                        inmatedict['Native State'] = "N/A"
            inmatelst.append(inmatedict)
    return inmatelst

#Passes in list of inmate dictionaries.  For each inmate dictionary, grab last statement
#Make the API call using requests.post, passing in the last statement, returned is JSON dictionary
#Convert sentiments into an integer scale for regression analysis
#Update dictionary
def calltoapi(inmatelst):
    for inmatedict in inmatelst:
        laststatement = inmatedict['Last Statement']
        exestr = requests.post(url='http://text-processing.com/api/sentiment/', data="text=" + laststatement + '"').content
        result = eval(exestr)
        inmatedict['Sentiment'] = str(result['label'])
        if inmatedict['Sentiment'] == 'neg':
            inmatedict['Sentiment'] = -1
        elif inmatedict['Sentiment'] == 'neutral':
            inmatedict['Sentiment'] = 0
        elif inmatedict['Sentiment'] == 'pos':
            inmatedict['Sentiment'] = 1

    return inmatelst

#Passes into list of dictionaries to be written to CSV file
#Keeps count of rows written
def writetocsv(inmatelstwithsentiment):
    with open('exinmates.csv', 'w', newline='') as output_file:
        inmate_file_writer = csv.DictWriter(output_file,
                                            fieldnames=['Execution No.', 'TDCJ Number', 'First Name', 'Last Name',
                                                        'Date Received', 'Age Received', 'Date of Offense',
                                                        'Age at Offense', 'Execution Date', 'Age', 'Gender', 'DOB',
                                                        'Race', 'County', 'Education Level', 'Weight',
                                                        'Eye Color', 'Hair Color', 'Native State', 'Last Statement',
                                                        'Sentiment', 'More Info URL', 'Last Statement URL'],
                                            extrasaction='ignore',
                                            delimiter=',', quotechar='"')
        inmate_file_writer.writeheader()
        row_count = 0
        for inmatedict in inmatelstwithsentiment:

            inmate_file_writer.writerow({'Execution No.': inmatedict['Execution No.'],
                                         'TDCJ Number': inmatedict['TDCJ Number'],
                                         'First Name': inmatedict['First Name'],
                                         'Last Name': inmatedict['Last Name'],
                                         'Date Received': inmatedict['Date Received'],
                                         'Age Received': inmatedict['Age Received'],
                                         'Date of Offense': inmatedict['Date of Offense'],
                                         'Age at Offense': inmatedict['Age at Offense'],
                                         'Execution Date': inmatedict['Execution Date'],
                                         'Execution Age': inmatedict['Execution Age'],
                                         'Gender': inmatedict['Gender'],
                                         'DOB': inmatedict['DOB'],
                                         'Race': inmatedict['Race'],
                                         'County': inmatedict['County'],
                                         'Education Level': inmatedict['Education Level'],
                                         'Weight': inmatedict['Weight'],
                                         'Eye Color': inmatedict['Eye Color'],
                                         'Hair Color': inmatedict['Hair Color'],
                                         'Native State': inmatedict['Native State'],
                                         'Last Statement': inmatedict['Last Statement'],
                                         'Sentiment': inmatedict['Sentiment'],
                                         'More Info URL': inmatedict['More Info URL'],
                                         'Last Statement URL': inmatedict['Last Statement URL']})
            row_count += 1
    print ("Done! Wrote a total of " + str(row_count) + " rows!")

def main():

    inmatelst = gettabledata()


    inmatelstwithsentiment = calltoapi(inmatelst)

    writetocsv(inmatelstwithsentiment)

if __name__ == '__main__':
    main()