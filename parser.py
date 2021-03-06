import nltk
import requests
from bs4 import BeautifulSoup
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
from nltk import pos_tag, word_tokenize
import re
import string
from transform import replace_ingredients, replace_instructions
from vegetarian_transform import vegetarian, not_vegetarian
from to_healthy_transform import to_healthy
from from_healthy_transform import from_healthy
from to_chinese_transform import to_chinese
from to_mexican_transform import to_mexican

def convertToFraction(test):
    fractions = {
        0x2189: 0.0,  # ; ; 0 # No       VULGAR FRACTION ZERO THIRDS
        0x2152: 0.1,  # ; ; 1/10 # No       VULGAR FRACTION ONE TENTH
        0x2151: 0.11111111,  # ; ; 1/9 # No       VULGAR FRACTION ONE NINTH
        0x215B: 0.125,  # ; ; 1/8 # No       VULGAR FRACTION ONE EIGHTH
        0x2150: 0.14285714,  # ; ; 1/7 # No       VULGAR FRACTION ONE SEVENTH
        0x2159: 0.16666667,  # ; ; 1/6 # No       VULGAR FRACTION ONE SIXTH
        0x2155: 0.2,  # ; ; 1/5 # No       VULGAR FRACTION ONE FIFTH
        0x00BC: 0.25,  # ; ; 1/4 # No       VULGAR FRACTION ONE QUARTER
        0x2153: 0.33333333,  # ; ; 1/3 # No       VULGAR FRACTION ONE THIRD
        0x215C: 0.375,  # ; ; 3/8 # No       VULGAR FRACTION THREE EIGHTHS
        0x2156: 0.4,  # ; ; 2/5 # No       VULGAR FRACTION TWO FIFTHS
        0x00BD: 0.5,  # ; ; 1/2 # No       VULGAR FRACTION ONE HALF
        0x2157: 0.6,  # ; ; 3/5 # No       VULGAR FRACTION THREE FIFTHS
        0x215D: 0.625,  # ; ; 5/8 # No       VULGAR FRACTION FIVE EIGHTHS
        0x2154: 0.66666667,  # ; ; 2/3 # No       VULGAR FRACTION TWO THIRDS
        0x00BE: 0.75,  # ; ; 3/4 # No       VULGAR FRACTION THREE QUARTERS
        0x2158: 0.8,  # ; ; 4/5 # No       VULGAR FRACTION FOUR FIFTHS
        0x215A: 0.83333333,  # ; ; 5/6 # No       VULGAR FRACTION FIVE SIXTHS
        0x215E: 0.875,  # ; ; 7/8 # No       VULGAR FRACTION SEVEN EIGHTHS
    }

    rx = r'(?u)([+-])?(\d*)(%s)' % '|'.join(map(chr, fractions))

    for sign, d, f in re.findall(rx, test):
        sign = -1 if sign == '-' else 1
        d = int(d) if d else 0
        number = sign * (d + fractions[ord(f)])

    try:
        return (f, number)
    except:
        return -1

def convert_to_float(frac):
    try:
        return float(frac)
    except ValueError:
        num, denom = frac.split('/')
        try:
            leading, num = num.split(' ')
            whole = float(leading)
        except ValueError:
            whole = 0
        frac = float(num) / float(denom)
        return whole - frac if whole < 0 else whole + frac

def getRecipe(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    return soup

def getTitle(soup):
    title = str(soup.title.text)
    return title

def getSteps(soup):
    result = []
    directions = soup.find_all("div", class_= "section-body")
    for direction in directions:
        x = direction.get_text().replace("\n", "").strip()
        result.append(x)

    result = result[:-1]
    return result

def getIngredients(soup):

    ingredients = soup.find_all("li", class_="ingredients-item")
    if not ingredients:
        #do this later
        pass
    result = []
    for ingredient in ingredients:
        x = ingredient.label.text.replace("\n", "").strip()
        numbers = convertToFraction(x)
        if numbers == -1:
            result.append(x)
        else:
            x = x.replace(numbers[0], str(numbers[1]))
            result.append(x)

    x = getIngredientParts(result)
    return x, result

def getIngredientParts(ingredients):

    measurements = ['tablespoon', 'tablespoons', 'ounce', 'ounces', 'teaspoon', 'teaspoons', 'cup', 'cups', 'quart',
                    'quarts', 'pint', 'pints', 'gallon', 'gallons', 'pound', 'pounds', 'pinch', 'package', 'packages',
                    'pound', 'pounds', 'slice', 'slices', 'packet', 'packets', 'cube', 'cubes', 'quart', 'quarts',
                    'halves', 'jar', 'jars', 'inch', 'inches']

    descriptors = ['ground', 'all-purpose', 'extra-virgin', 'unsweetened', 'provolone']

    keywords = ['black']

    finalIngredients = []


    for ingredient in ingredients:
        shouldContinue = False
        ingredientName = ""
        quantity = 0
        measurement = ""
        descriptor = ""
        preparation = ""
        text = word_tokenize(ingredient)

        test = pos_tag(text)

        for i in range(0, len(text)):
            if shouldContinue:
                shouldContinue = False
                continue

            if test[i][1] == 'CD':
                try:
                    x = convert_to_float(text[i])
                    quantity += x
                except:
                    if text[i] in descriptors:
                        if descriptors != "":
                            descriptor += ' ' + text[i]
                        else:
                            descriptor += text[i]

            else:
                if text[i] in measurements:
                    measurement += text[i]
                else:
                    if text[i] in keywords:
                        if ingredientName != "":
                            ingredientName += ' and ' + text[i] + ' ' + text[i + 1]
                            shouldContinue = True
                        else:
                            ingredientName += text[i] + ' ' + text[i + 1]
                            shouldContinue = True
                    elif text[i] in descriptors:
                        if descriptors != "":
                            descriptor += ' ' + text[i]
                        else:
                            descriptor += text[i]
                    elif test[i][1] == 'JJ':
                        if descriptors != "":
                            descriptor += ' ' + text[i]
                        else:
                            descriptor += text[i]
                    elif test[i][1] == 'NN' or test[i][1] == 'NNS':
                        if ingredientName != "":
                            ingredientName += ' ' + text[i]
                        else:
                            ingredientName += text[i]
                    elif test[i][1] == 'RB':
                        #for adverbs, eg 'finely chopped'
                        if preparation != "":
                            preparation += ' and ' + text[i] + ' ' + text[i + 1]
                            shouldContinue = True
                        else:
                            preparation += text[i] + ' ' + text[i + 1]
                            shouldContinue = True
                    elif test[i][1] == 'VBN' or test[i][1] == 'VBD':
                        if preparation != "":
                            preparation += ' and ' + text[i]
                        else:
                            preparation += text[i]

        ingredientObj = {
            "name": ingredientName,
            "quantity": str(quantity),
            "measurement": measurement,
            "descriptor": descriptor,
            "preparation": preparation
        }
        finalIngredients.append(ingredientObj)

    return finalIngredients

def getTools(directions):
    table = str.maketrans(dict.fromkeys(string.punctuation))
    toolsList = ['knife', 'cutting board', 'can opener', 'bowl', 'bowls', 'colander', 'peeler', 'masher',
                 'potato masher', 'whisk', 'grater', 'shears', 'shear', 'juicer', 'skillet', 'pan', 'pans',
                 'pot', 'pots', 'saucepan', 'stockpot', 'spatula', 'stirring spoon', 'spoon', 'tongs',
                 'ladle', 'oven mitts', 'trivet', 'splatter guard', 'thermometer', 'blender', 'scale', 'container',
                 'aluminum foil', 'parchment paper', 'towel', 'towels', 'food processor', 'grill', 'baster',
                 'beanpot', 'brush', 'basket', 'timer', 'sheet', 'baking sheet', 'poacher', 'grittle', 'grater',
                 'grinder', 'griddle', 'mixer', 'microwave', 'oven', 'strainer', 'steamer', 'scissors', 'sieve',
                 'skewer', 'wok', 'zester', 'plate', 'mortar', 'pestle', 'gloves', 'cookie cutter', 'cookie sheet',
                 'cookie sheets', 'bread knife', 'cheese grater', 'cheese cutter', 'cheese knife', 'pizza wheel',
                 'pizza cutter', 'soup ladle', 'rolling pin', 'baking dish', 'baking pan', 'baking sheet', 'baking sheets',
                 'air fryer', 'shallow dish', 'container', 'containers']

    returnList = []
    for i in range(len(directions)):
        bigrams = list(nltk.bigrams(directions[i].lower().split()))
        for x in bigrams:
            two_words = x[0] + ' ' + x[1]
            two_words = two_words.translate(table)
            if two_words in toolsList:
                returnList.append(two_words)

        words = directions[i].lower().split()
        for x in words:
            x = x.translate(table)
            test = [y.split() for y in returnList]
            combined = []
            for j in test:
                combined = combined + j

            if x in toolsList and x not in combined and x not in returnList:
                returnList.append(x)

    return returnList


def getMethods(directions):
    table = str.maketrans(dict.fromkeys(string.punctuation))
    possibleMethods = ['bake', 'heat', 'cook', 'boil', 'saute', 'broil', 'poach', 'roast', 'steam']

    resultList = []
    for i in range(len(directions)):
        directionCleaned = directions[i].translate(table).lower()
        for word in directionCleaned.split():
            if word in possibleMethods:
                if word not in resultList:
                    resultList.append(word)

    return resultList

def main(url, transform, passed_steps, passed_ingredients):
    stillRunning = True
    if url == '0':
        stillRunning = False

    while stillRunning:

        if transform == "vegetarian":
            transform_dict = vegetarian
        elif transform == "non-vegetarian":
            transform_dict = not_vegetarian
        elif transform == "healthy":
            transform_dict = to_healthy
        elif transform == "non-healthy":
            transform_dict = from_healthy
        elif transform == "Chinese":
            transform_dict = to_chinese
        elif transform == "Mexican":
            transform_dict = to_mexican
        else:
            raise Exception("Transform does not exist")

        try:
            recipeSoup = getRecipe(url)
        except:
            print("Invalid URL")
            exit(0)

        if passed_ingredients == None or passed_steps == None:

            title = getTitle(recipeSoup)
            ingredients = getIngredients(recipeSoup)[0]
            steps = getSteps(recipeSoup)
            tools = getTools(steps)
            methods = getMethods(steps)

            print("Recipe Title: " + title + '\n')

            print("Recipe Ingredients (before transformation): ")
            for i in range(0, len(ingredients)):
                print(str(i + 1) + '. ' + ingredients[i]['name'])
                print("quantity: " + ingredients[i]['quantity'])
                print("measurement: " + ingredients[i]['measurement'])
                print("descriptor: " + ingredients[i]['descriptor'])
                print("preparation: " + ingredients[i]['preparation'] + '\n')

            # print(ingredients)
            # print('\n')
            print("Recipe Tools: ")
            for i in range(0, len(tools)):
                print(str(i + 1) + '. ' + tools[i])

            print("\nRecipe Methods: ")
            for i in range(0, len(methods)):
                print(str(i + 1) + '. ' + methods[i])

            print("\nRecipe Steps: (before transformation): ")
            for i in range(0, len(steps)):
                print(str(i + 1) + '. ' + steps[i])

        print("\nAfter transformation: " + '\n')


        ingredients = getIngredients(recipeSoup)[1]

        if passed_ingredients == None:
            new_ingredients = replace_ingredients(ingredients, transform_dict)
        else:
            new_ingredients = replace_ingredients(passed_ingredients, transform_dict)

        print("Ingredients: ")
        for i in range(0, len(new_ingredients)):
            print(str(i + 1) + '. ' + new_ingredients[i])

        if passed_steps == None:
            new_steps = replace_instructions(steps, transform_dict, ingredients, transform)
        else:
            new_steps = replace_instructions(passed_steps, transform_dict, ingredients, transform)


        print("\nSteps: ")
        for i in range(0, len(new_steps)):
            print(str(i + 1) + '. ' + new_steps[i])

        nextStep = input("\nWould you like to choose a new transform or a new recipe? (transform or recipe): " )
        if nextStep == 'transform':
            transformType = input('Please enter what transformation you would like (vegetarian, non-vegetarian, healthy, non-healthy, Chinese, Mexican): ')
            main(url, transformType, new_steps, new_ingredients)
        elif nextStep == 'recipe':
            recipeUrl = input('\nPlease enter a URL for a recipe from AllRecipes.com (enter 0 to exit): ')
            if recipeUrl == '0':
                exit(0)
            transformType = input('Please enter what transformation you would like (vegetarian, non-vegetarian, healthy, non-healthy, Chinese, Mexican): ')
            main(recipeUrl, transformType, None, None)
        else:
            print("Invalid entry")
            exit(0)



if __name__ == '__main__':
    recipeUrl = input('Please enter a URL for a recipe from AllRecipes.com (enter 0 to exit): ')
    if recipeUrl == '0':
        exit(0)
    transformType = input('Please enter what transformation you would like (vegetarian, non-vegetarian, healthy, non-healthy, Chinese, Mexican): ')
    main(recipeUrl, transformType, None, None)
