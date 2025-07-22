package main

import (
	"context"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"os"
	"runtime/pprof"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/grafana/pyroscope-go"
)

// Simulate different types of workloads

//go:noinline
func cpuIntensiveWork(n int) {
	// CPU-bound work with actual computation
	sum := 0.0
	for i := 0; i < n; i++ {
		sum += math.Sqrt(float64(i)) * math.Sin(float64(i))
	}
	_ = sum // prevent optimization
}

//go:noinline
func memoryIntensiveWork(size int) {
	// Memory allocation and manipulation
	data := make([][]byte, size)
	for i := range data {
		data[i] = make([]byte, 1024)
		rand.Read(data[i])
	}

	// Some processing to prevent optimization
	for i := range data {
		for j := range data[i] {
			data[i][j] = byte((int(data[i][j]) + i + j) % 256)
		}
	}
}

//go:noinline
func recursiveFibonacci(n int) int {
	if n <= 1 {
		return n
	}
	return recursiveFibonacci(n-1) + recursiveFibonacci(n-2)
}

//go:noinline
func recursiveFactorial(n int) int {
	if n <= 1 {
		return 1
	}
	return n * recursiveFactorial(n-1)
}

//go:noinline
func stringProcessing(iterations int) {
	var builder strings.Builder
	for i := 0; i < iterations; i++ {
		builder.WriteString(fmt.Sprintf("iteration-%d-", i))
	}

	// JSON marshaling/unmarshaling
	data := map[string]interface{}{
		"message": builder.String(),
		"count":   iterations,
		"nested": map[string]int{
			"a": 1, "b": 2, "c": 3,
		},
	}

	jsonData, _ := json.Marshal(data)
	var result map[string]interface{}
	json.Unmarshal(jsonData, &result)
}

//go:noinline
func sortingWork(size int) {
	// Create random data
	data := make([]int, size)
	for i := range data {
		data[i] = int(time.Now().UnixNano()) % 10000
	}

	// Multiple sorting algorithms
	data1 := make([]int, len(data))
	copy(data1, data)
	sort.Ints(data1)

	// Bubble sort for smaller datasets (inefficient by design)
	if size <= 1000 {
		data2 := make([]int, len(data))
		copy(data2, data)
		bubbleSort(data2)
	}
}

//go:noinline
func bubbleSort(arr []int) {
	n := len(arr)
	for i := 0; i < n-1; i++ {
		for j := 0; j < n-i-1; j++ {
			if arr[j] > arr[j+1] {
				arr[j], arr[j+1] = arr[j+1], arr[j]
			}
		}
	}
}

//go:noinline
func networkSimulation(requests int) {
	// Simulate network-like delays and processing
	for i := 0; i < requests; i++ {
		// Simulate variable latency
		latency := time.Duration(10+i%50) * time.Microsecond
		time.Sleep(latency)

		// Simulate request processing
		processRequest(i)
	}
}

//go:noinline
func processRequest(id int) {
	// Simulate request processing with string operations
	request := fmt.Sprintf("request-%d", id)
	parts := strings.Split(request, "-")
	if len(parts) > 1 {
		num, _ := strconv.Atoi(parts[1])
		_ = num * 2
	}
}

//go:noinline
func concurrentWork(ctx context.Context, workers int) {
	var wg sync.WaitGroup

	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()
			pyroscope.TagWrapper(ctx, pyroscope.Labels("worker", fmt.Sprintf("worker-%d", workerID)), func(c context.Context) {
				// Each worker does different types of work
				switch workerID % 3 {
				case 0:
					cpuIntensiveWork(1000000)
				case 1:
					memoryIntensiveWork(500)
				case 2:
					stringProcessing(10000)
				}
			})
		}(i)
	}

	wg.Wait()
}

// Different function types for varied flame graph patterns

func fastFunction(c context.Context) {
	pyroscope.TagWrapper(c, pyroscope.Labels("function", "fast", "type", "cpu"), func(c context.Context) {
		cpuIntensiveWork(1000000)
	})
}

func slowFunction(c context.Context) {
	pprof.Do(c, pprof.Labels("function", "slow", "type", "mixed"), func(c context.Context) {
		cpuIntensiveWork(5000000)
		memoryIntensiveWork(200)
	})
}

func recursiveFunction(c context.Context) {
	pyroscope.TagWrapper(c, pyroscope.Labels("function", "recursive", "type", "fibonacci"), func(c context.Context) {
		// Fibonacci creates deep call stacks
		result := recursiveFibonacci(35)
		_ = result
	})
}

func memoryFunction(c context.Context) {
	pyroscope.TagWrapper(c, pyroscope.Labels("function", "memory", "type", "allocation"), func(c context.Context) {
		memoryIntensiveWork(1000)
	})
}

func stringFunction(c context.Context) {
	pyroscope.TagWrapper(c, pyroscope.Labels("function", "string", "type", "processing"), func(c context.Context) {
		stringProcessing(50000)
	})
}

func sortingFunction(c context.Context) {
	pyroscope.TagWrapper(c, pyroscope.Labels("function", "sorting", "type", "algorithms"), func(c context.Context) {
		sortingWork(5000)
	})
}

func networkFunction(c context.Context) {
	pyroscope.TagWrapper(c, pyroscope.Labels("function", "network", "type", "simulation"), func(c context.Context) {
		networkSimulation(100)
	})
}

func mathFunction(c context.Context) {
	pyroscope.TagWrapper(c, pyroscope.Labels("function", "math", "type", "factorial"), func(c context.Context) {
		result := recursiveFactorial(15)
		_ = result
	})
}

func concurrentFunction(c context.Context) {
	pyroscope.TagWrapper(c, pyroscope.Labels("function", "concurrent", "type", "goroutines"), func(c context.Context) {
		concurrentWork(c, 10)
	})
}

func main() {
	serverAddress := os.Getenv("PYROSCOPE_SERVER_ADDRESS")
	if serverAddress == "" {
		serverAddress = "http://localhost:4040"
	}

	_, err := pyroscope.Start(pyroscope.Config{
		ApplicationName: "sample_app",
		ServerAddress:   serverAddress,
		Logger:          pyroscope.StandardLogger,
		Tags: map[string]string{
			"version": "2.0",
			"env":     "demo",
		},
	})
	if err != nil {
		log.Fatalf("error starting pyroscope profiler: %v", err)
	}

	// Main execution loop with varied workloads
	pyroscope.TagWrapper(context.Background(), pyroscope.Labels("phase", "main"), func(c context.Context) {
		iteration := 0
		for {
			iteration++

			// Create varied execution patterns
			switch iteration % 9 {
			case 0:
				fastFunction(c)
			case 1:
				slowFunction(c)
			case 2:
				recursiveFunction(c)
			case 3:
				memoryFunction(c)
			case 4:
				stringFunction(c)
			case 5:
				sortingFunction(c)
			case 6:
				networkFunction(c)
			case 7:
				mathFunction(c)
			case 8:
				concurrentFunction(c)
			}

			// Occasional heavy computation phase
			if iteration%20 == 0 {
				pyroscope.TagWrapper(c, pyroscope.Labels("phase", "heavy"), func(c context.Context) {
					cpuIntensiveWork(10000000)
					memoryIntensiveWork(2000)
				})
			}

			// Short pause to make the profiling more readable
			time.Sleep(10 * time.Millisecond)
		}
	})
}
