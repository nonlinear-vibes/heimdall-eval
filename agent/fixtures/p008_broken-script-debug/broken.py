def average(numbers):
    total = 0
    for n in numbers
        total += n
    return total / len(numbers)
 
 
def main():
    scores = [88, 92, 79, 95, 84]
    result = average(scores)
    print(f"Average score: {result}")
 
    empty_result = average(empty_scores)
    print(f"Average of empty list: {empty_result}")
 
 
if __name__ == "__main__":
    main()
