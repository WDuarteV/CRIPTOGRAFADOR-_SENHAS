CXX = g++
CXXFLAGS = -O3 -std=c++17 -Wall -Wextra
TARGET = app
SRC = main.cpp

all: $(TARGET)

$(TARGET): $(SRC) ../common/keyword_crypto.hpp
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(SRC)

clean:
	rm -f $(TARGET)

.PHONY: all clean
