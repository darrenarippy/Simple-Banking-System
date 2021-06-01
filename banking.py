from random import randint
import sqlite3
import os


class Bank:
    iin = 400000

    def __init__(self):
        db_exists = os.path.exists("card.s3db")
        self.db = sqlite3.connect("card.s3db")
        self.cursor = self.db.cursor()
        if not db_exists:
            self.cursor.execute("CREATE TABLE card ("
                                "id INTEGER, number TEXT,"
                                "pin TEXT,"
                                "balance INTEGER DEFAULT 0);")
            self.db.commit()

    def operate(self):
        while True:
            self.display_bank_menu()
            customer_selection = input()
            while customer_selection not in ["0", "1", "2"]:
                print()
                self.display_bank_menu()
                customer_selection = input()
            if customer_selection != "0":
                if customer_selection == "1":
                    self.create_an_account()
                else:
                    credentials = self.validate_credentials()
                    if len(credentials) == 0:
                        print("\nWrong card number or PIN!\n")
                    else:
                        exit_bank = self.access_account(credentials)
                        if exit_bank:
                            break
            else:
                break
        self.db.close()
        print("\nBye!")

    @staticmethod
    def display_bank_menu():
        menu = "1. Create an account\n" + \
               "2. Log into account\n" + \
               "0. Exit"
        print(menu)

    def create_an_account(self):
        account_id = self.generate_account_id()
        check_sum = self.generate_check_sum(account_id)
        new_account = CreditCard(Bank.iin, account_id, check_sum)
        self.add_account(new_account)
        print("\nYour card has been created")
        print("Your card number:")
        print(new_account.get_card_number())
        print("Your card PIN:")
        print(new_account.get_pin())
        print()

    def generate_account_id(self):
        account_ids = self.get_account_ids()
        account_id = randint(0, 999999999)
        while account_id in account_ids:
            account_id = randint(0, 999999999)
        return account_id

    @staticmethod
    def generate_check_sum(account_id):
        """
        Implements the Luhn Algorithm to generate an appropriate checksum.
        :param account_id: an integer between 0 and 999999999
        :return: an integer between 0 and 9
        """
        card_number = str(Bank.iin) + str(account_id).zfill(9)
        step_one = []
        for i in range(len(card_number)):
            digit = int(card_number[i])
            if i % 2 == 0:
                digit *= 2
                if digit > 9:
                    digit -= 9
            step_one.append(digit)
        step_two = sum(step_one)
        remainder = step_two % 10
        check_sum = (10 - remainder) if remainder else remainder
        return check_sum

    def get_account_ids(self):
        self.cursor.execute("SELECT id FROM card;")
        account_ids = [account_id for row in self.cursor.fetchall() for account_id in row]
        return account_ids

    def add_account(self, credit_card_account):
        self.cursor.execute("""INSERT INTO card 
                                VALUES (:id, :number, :pin, :balance);""",
                            {"id": int(credit_card_account.get_account_id()),
                             "number": credit_card_account.get_card_number(),
                             "pin": credit_card_account.get_pin(),
                             "balance": credit_card_account.get_balance()})
        self.db.commit()

    def get_account(self, account_id):
        self.cursor.execute("""SELECT *
                               FROM card
                               WHERE id = :id;""",
                            {"id": account_id})
        record = self.cursor.fetchone()
        account_id = record[0]
        check_sum = int(record[1][-1])
        pin = int(record[2])
        balance = record[3]
        account = CreditCard(bank.iin, account_id, check_sum, pin, balance)
        return account

    def validate_credentials(self):
        card_number = input("\nEnter your card number:\n")
        card_pin = input("Enter your PIN:\n")
        credentials = []
        if self.validate_card_number(card_number):
            if self.validate_card_pin(card_number, card_pin):
                account_id = int(card_number[6:15])
                credentials = [account_id, card_pin]
        return credentials

    def validate_card_number(self, card_number):
        iin = int(card_number[:6])
        account_id = int(card_number[6:15])
        account_ids = self.get_account_ids()
        return (iin == self.iin) and (account_id in account_ids)

    def validate_card_pin(self, card_number, card_pin):
        account_id = int(card_number[6:15])
        return card_pin == self.get_account(account_id).get_pin()

    def validate_checksum(self, card_number):
        account_id = int(card_number[6:15])
        check_sum = int(card_number[-1])
        return check_sum == self.generate_check_sum(account_id)

    def access_account(self, credentials):
        print("\nYou have successfully logged in!\n")
        account_id = credentials[0]
        card = self.get_account(account_id)
        return self.process_account(card)

    def process_account(self, card):
        while True:
            card.display_card_menu()
            customer_selection = input()
            exit_bank = False
            while customer_selection not in [str(i) for i in range(6)]:
                print()
                card.display_card_menu()
                customer_selection = input()
            if customer_selection != "0":
                if customer_selection == "1":
                    print("\nBalance: {}\n".format(card.get_balance()))
                elif customer_selection == "2":
                    deposit_amount = int(input("\nEnter income:\n"))
                    card.deposit_money(self.db, self.cursor, deposit_amount)
                    print("Income was added!\n")
                elif customer_selection == "3":
                    self.attempt_transfer(card)
                elif customer_selection == "4":
                    self.close_an_account(card)
                    break
                else:
                    print("\nYou have successfully logged out!\n")
                    break
            else:
                exit_bank = True
                break
        return exit_bank

    def attempt_transfer(self, from_card):
        to_card_number = input("\nTransfer\nEnter your card number:\n")
        if self.validate_checksum(to_card_number):
            if self.validate_card_number(to_card_number):
                prompt = "Enter how much money you want to transfer:\n"
                transfer_amount = int(input(prompt))
                if from_card.validate_balance(transfer_amount):
                    self.perform_transfer(from_card, to_card_number, transfer_amount)
                else:
                    print("Not enough money!\n")
            else:
                print("Such a card does not exist.\n")
        else:
            print("Probably you made a mistake in the card number.")
            print("Please try again!\n")

    def perform_transfer(self, from_card, to_card_number, amount):
        to_account_id = to_card_number[6:15]
        to_card = self.get_account(to_account_id)
        from_card.withdraw_money(self.db, self.cursor, amount)
        to_card.deposit_money(self.db, self.cursor, amount)
        print("Success!\n")

    def close_an_account(self, card):
        self.cursor.execute("""DELETE FROM card
                               WHERE id = :account_id""",
                            {"account_id": int(card.get_account_id())})
        self.db.commit()
        print("\nThe account has been closed!\n")


class CreditCard:
    def __init__(self, iin, account_id, check_sum, pin=randint(0, 9999), balance=0):
        self.iin = iin
        self.account_id = account_id
        self.check_sum = check_sum
        self.pin = pin
        self.balance = balance

    @staticmethod
    def display_card_menu():
        menu = "1. Balance\n" + \
               "2. Add income\n" \
               "3. Do transfer\n" \
               "4. Close account\n" \
               "5. Log out\n" + \
               "0. Exit"
        print(menu)

    def get_account_id(self):
        account_id = "{}".format(self.account_id).zfill(9)
        return account_id

    def get_card_number(self):
        card_number = "{}".format(self.iin) \
                      + "{}".format(self.account_id).zfill(9) \
                      + "{}".format(self.check_sum)
        return card_number

    def get_pin(self):
        pin = "{}".format(self.pin).zfill(4)
        return pin

    def get_balance(self):
        balance = self.balance
        return balance

    def deposit_money(self, db, cursor, deposit_amount):
        self.balance += deposit_amount
        cursor.execute("""UPDATE card
                          SET balance = :bal
                          WHERE id = :account_id;""",
                       {"bal": self.get_balance(),
                        "account_id": int(self.get_account_id())})
        db.commit()

    def withdraw_money(self, db, cursor, withdrawal_amount):
        self.balance -= withdrawal_amount
        cursor.execute("""UPDATE card
                                  SET balance = :bal
                                  WHERE id = :account_id;""",
                       {"bal": self.get_balance(),
                        "account_id": int(self.get_account_id())})
        db.commit()

    def validate_balance(self, amount):
        return amount <= self.get_balance()


bank = Bank()
bank.operate()
