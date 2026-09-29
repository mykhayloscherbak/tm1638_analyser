
  # tm1638
  
## Description
* This decoder gets keyscan and LED data from the SPI half duplex protocol
* It has 2 modes - tm1638 for raw chip data decoding and QYF-TM1638 board 
* QYF-TM1638 mode shows the keyscans in format RyCx where y is a key row and x is a key column
* QYF-TM1638 decodes the symbol generator patterns from the  SEGMENT_SYMBOLS variable. You can add your own ones.
* Results can be seen in a table view
             

  