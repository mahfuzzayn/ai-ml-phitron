#include <stdio.h>

int findSmallest(int arr[], int size) {
    // Step 1: Assume the first element is the smallest
    int smallest = arr[0]; 
    
    // Step 2: Loop through the rest of the array
    for (int i = 1; i < size; i++) {
        // Step 3: Update if a smaller element is found
        if (arr[i] < smallest) {
            smallest = arr[i];
        }
    }
    
    return smallest;
}

int find_element_index(const int arr[], int size, int target) {
    for (int i = 0; i < size; i++) {
        if (arr[i] == target) {
            return i; // Return index immediately on match
        }
    }
    return -1; // Return -1 if the loop finishes without a match
}

int main()
{
    int n;

    // 3
    scanf("%d", &n);

    // size 3
    int arr[n];
    // 1, 2, 3

    for (int i = 0; i < n; i++) {
        scanf("%d", &arr[i]);
    }

    int smallest = findSmallest(arr, n);

    printf("%d ", smallest);
    printf("%d", find_element_index(arr, n, smallest)+1);

    return 0;
}