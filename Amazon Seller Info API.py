import time
import uvicorn
from selenium import webdriver
from Levenshtein import distance
from amazoncaptcha import AmazonCaptcha
from fastapi import FastAPI, HTTPException
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException

app = FastAPI()

# Global variables to store information between endpoints
list_elements = []
driver = None

# Function to check if the element is present
def is_element_present(driver):
    try:
        driver.find_element(By.ID, 'nav-global-location-popover-link')
        return True
    except NoSuchElementException:
        return False

@app.get("/get_locations")
def get_locations():
    global list_elements, driver
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    driver.get("https://www.amazon.com/errors/validateCaptcha")

    try:
        # Run the loop until the element appears
        while not is_element_present(driver):
            link = driver.find_element(By.XPATH, "//div[@class='a-row a-text-center']//img").get_attribute('src')
            captcha = AmazonCaptcha.fromlink(link)
            captcha_value = AmazonCaptcha.solve(captcha)
            driver.find_element(By.ID, 'captchacharacters').send_keys(captcha_value)
            button = driver.find_element(By.CLASS_NAME, 'a-button-text')
            button.click()

        time.sleep(5)
        slt_loc_btn = driver.find_element(By.ID, 'nav-global-location-popover-link')
        slt_loc_btn.click()

        time.sleep(5)
        dropdown_button = driver.find_element(By.XPATH, "//span[@class='a-button-text a-declarative']")
        dropdown_button.click()

        list_elements = driver.find_elements(By.XPATH, '//div[@class="a-popover-inner a-lgtbox-vertical-scroll"]/ul/li')

        elements_text = [li_element.text for li_element in list_elements]

        return {"locations": elements_text}
    
    except WebDriverException as e:
        return {"error": f"An error occurred: {e}"}

@app.post("/apply_filters")
def apply_filter(selected_item_index: int, search_item: str, brand_name: str, lower_price: int, upper_price: int, rating_input: int, min_rev_cnt: int, max_rev_cnt: int):
    global list_elements, driver

    try:
        if not list_elements or not driver:
            raise HTTPException(status_code=400, detail="Run /get_locations first to get elements")

        selected_item = list_elements[selected_item_index]
        selected_item.click()
        time.sleep(5)

        done_btn = driver.find_element(By.XPATH, '//button[@name="glowDoneButton"]')
        done_btn.click()
        time.sleep(5)

        driver.find_element(By.ID, 'twotabsearchtextbox').send_keys(f"{search_item}")

        driver.find_element(By.ID, 'nav-search-submit-button').click()

        time.sleep(5)

        driver.find_element(By.CSS_SELECTOR, '#brandsRefinements > ul > span > li > span > div > a > span').click()
        try:
            brand = driver.find_element(By.CSS_SELECTOR, "#brandsRefinements > ul:nth-child(4)")
        except NoSuchElementException:
            brand = driver.find_element(By.CSS_SELECTOR, "#brandsRefinements > ul")

        brand_list = brand.text.split('\n')

        def calculate_distance(string1, string2):
            return distance(string1, string2)

        # Find the brand with the closest match to the input value
        closest_brand = min(brand_list, key=lambda brand: calculate_distance(brand_name, brand))
        driver.find_element(By.CSS_SELECTOR, f'#p_89\/{closest_brand} > span > a').click()

        time.sleep(5)
        driver.find_element(By.CSS_SELECTOR, f"#reviewsRefinements > ul > span > span:nth-child({rating_input})").click()
        
        time.sleep(10)
        try:
            driver.find_element(By.CSS_SELECTOR, '#low-price').send_keys(f"{lower_price}")
            driver.find_element(By.CSS_SELECTOR, '#high-price').send_keys(f"{upper_price}")
            driver.find_element(By.CSS_SELECTOR, '#a-autoid-1 > span > input').click()

        except NoSuchElementException:
            lower = driver.find_element(By.CSS_SELECTOR, 'label.a-form-label.sf-range-slider-label.sf-lower-bound-label > span')
            lower_text = lower.text.split('$')[1]
            numeric_string = ''.join(filter(str.isdigit, lower_text))
            actual_lower_limit = int(numeric_string)

            upper = driver.find_element(By.CSS_SELECTOR, 'label.a-form-label.sf-range-slider-label.sf-upper-bound-label > span')
            upper_text = upper.text.split('$')[1]
            numeric_string = ''.join(filter(str.isdigit, upper_text))
            actual_upper_limit = int(numeric_string)

            user_input = 1
            if actual_lower_limit <= lower_price <= actual_upper_limit:
                repetition_limit = 10
                repetition_count = 0
                previous_result_integer = None  # Initialize the variable

                while True:
                    script = f"""
                        var slider = document.getElementById('p_36/range-slider_slider-item_lower-bound-slider');
                        slider.value = {user_input};
                        var event = new Event('input', {{ bubbles: true }});
                        slider.dispatchEvent(event);
                    """
                    driver.execute_script(script)
                    
                    # Get the text of the element
                    lower = driver.find_element(By.CSS_SELECTOR, 'label.a-form-label.sf-range-slider-label.sf-lower-bound-label > span')
                    lower_text = lower.text.split('$')[1]
                    numeric_string = ''.join(filter(str.isdigit, lower_text))
                    result_integer = int(numeric_string)
                    print("lower_text", result_integer)
                    print("user_input", user_input)

                    # Check if the text equals the desired value
                    if result_integer >= lower_price:
                        break

                    # Increment user_input for the next iteration
                    user_input += 1

                    # Check if the result_integer repeats
                    if result_integer == previous_result_integer:
                        repetition_count += 1
                        if repetition_count >= repetition_limit:
                            break
                    else:
                        repetition_count = 0

                    # Update the previous result for the next iteration
                    previous_result_integer = result_integer

            else:
                print("Invalid Lower Input")
                
            # Setting the upper price limit
            user_input = 189
            if actual_lower_limit <= upper_price <=actual_upper_limit:
                repetition_limit = 20
                repetition_count = 0
                previous_result_integer = None  # Initialize the variable
                
                while True:
                    script = f"""
                        var slider = document.getElementById('p_36/range-slider_slider-item_upper-bound-slider');
                        slider.value = {user_input};
                        var event = new Event('input', {{ bubbles: true }});
                        slider.dispatchEvent(event);
                    """
                    driver.execute_script(script)
                
                    # Get the text of the element
                    upper = driver.find_element(By.CSS_SELECTOR, 'label.a-form-label.sf-range-slider-label.sf-upper-bound-label > span')
                    upper_text = upper.text.split('$')[1]
                    numeric_string = ''.join(filter(str.isdigit, upper_text))
                    result_integer = int(numeric_string)
                    
                    print("upper_text", result_integer)
                    print("user_input", user_input)
                    # Check if the text equals the desired value
                    if result_integer <= upper_price:
                        break
                    # Increment user_input for the next iteration
                    user_input -= 1

                    # Check if the result_integer repeats
                    if result_integer == previous_result_integer:
                        repetition_count += 1
                        if repetition_count >= repetition_limit:
                            break
                    else:
                        repetition_count = 0

                    # Update the previous result for the next iteration
                    previous_result_integer = result_integer

            else:
                print("Invalid Upper Input")

            time.sleep(3)
            price_go = driver.find_element(By.CSS_SELECTOR, '#a-autoid-1 > span > input')
            price_go.click()
            time.sleep(10)
        
        product_n_seller_info = []

        start_page, end_page = 1, 2
        for i in range(start_page, end_page):
            elements = driver.find_elements(By.CSS_SELECTOR, '.puis-card-border')
            for ele in range(len(elements)):
                elements = driver.find_elements(By.CSS_SELECTOR, '.puis-card-border')
                element = elements[ele]
                lines = element.text.split('\n')

                for j in range(len(lines)):
                    lines[j] = lines[j].replace(',', '')

                    if lines[j].isdigit():
                        li = lines[j].split('\n')
                        for l in li:
                            if min_rev_cnt <= int(l) <= max_rev_cnt:
                                try:
                                    product_n_seller_info.append("Product Info")
                                    product_n_seller_info.append(element.text)

                                    print("Click to the element")
                                    print("element: ", element)
                                    element.click()
                                    time.sleep(5)
                                    
                                    try:
                                        # offer_message = driver.find_element(By.XPATH, '//span[@class="a-size-small offer-display-feature-text-message"]').text
                                        offer_message = driver.find_element(By.CSS_SELECTOR, "#merchantInfoFeature_feature_div > div.offer-display-feature-text > div > span").text
                                        product_n_seller_info.append("Seller Info")
                                        product_n_seller_info.append(offer_message)
                                        driver.back()

                                    except NoSuchElementException:
                                        try:
                                            see_all_buying_opt = driver.find_element(By.CSS_SELECTOR, '#buybox-see-all-buying-choices > span > a')
                                            see_all_buying_opt.click()
                                            time.sleep(10)
                                            link_element = driver.find_element(By.CSS_SELECTOR, '#aod-offer-soldBy > div > div > div.a-fixed-left-grid-col.a-col-right > a')
                                            driver.execute_script("arguments[0].target = '_self'; arguments[0].click();", link_element)
                                            time.sleep(5)
                                            seller_info = driver.find_element(By.XPATH, '//*[@id="page-section-detail-seller-info"]/div/div/div').text
                                            product_n_seller_info.append("Seller Info")
                                            product_n_seller_info.append(seller_info)
                                            driver.back()
                                            time.sleep(2)
                                            driver.back()
                                            time.sleep(2)
                                            driver.back()

                                        except NoSuchElementException as e:
                                            continue

                                except Exception as e:
                                    continue

                                break
        return {"product_n_seller_info": product_n_seller_info}
        # return {"filtered applied successfully"}

    except IndexError:
        return {"product_n_seller_info": product_n_seller_info}
        # raise HTTPException(status_code=400, detail="Invalid selected_item_index")

    except WebDriverException as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
