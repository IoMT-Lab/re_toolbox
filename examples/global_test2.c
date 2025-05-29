#include <stdio.h>
#include <stdlib.h>
#include <string.h>


typedef struct {
    int id;
    char name[50];
    float balance;
    struct {
        int day;
        int month;
        int year;
    } dateOfBirth;
    void (*callback)(int);
} User;


typedef void (*FunctionPointer)(User*);

void displayUser(User* user);
void updateUserBalance(User* user);
void processCallback(int id);
void handleFunction(FunctionPointer func, User* user);
User user0  =   {
        .id = 1,
        .name = "Alice",
        .balance = 1000.0f,
        .dateOfBirth = {15, 8, 1990},
        .callback = processCallback
    };

int main() {
    User user1;
    user1 = user0;

    User user2 = {
        .id = 2,
        .name = "Bob",
        .balance = 1500.0f,
        .dateOfBirth = {20, 5, 1985},
        .callback = processCallback
    };

    

    FunctionPointer functions[] = {displayUser, updateUserBalance};
    
    for (int i = 0; i < 2; ++i) {
        handleFunction(functions[i], &user1);
        handleFunction(functions[i], &user2);
    }


    user1.callback(user1.id);
    user2.callback(user2.id);
    return 0;
}


void displayUser(User* user) {
    printf("User ID: %d\n", user->id);
    printf("Name: %s\n", user->name);
    printf("Balance: %.2f\n", user->balance);
    printf("Date of Birth: %02d-%02d-%04d\n", user->dateOfBirth.day, user->dateOfBirth.month, user->dateOfBirth.year);
}


void updateUserBalance(User* user) {
    user->balance += 100;
    printf("Updated Balance for User ID %d: %.2f\n", user->id, user->balance);
}


void processCallback(int id) {
    printf("Callback called for User ID: %d\n", id);
}


void handleFunction(FunctionPointer func, User* user) {
    if (func == updateUserBalance) {
        func(user);  
    } else {
        func(user);      }
}
