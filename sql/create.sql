USE [master]

GO

PRINT 'Create database - Start'

	CREATE DATABASE [Booking] 
		-- CONTAINMENT = NONE
		-- ON  PRIMARY 
		-- ( 
		-- 	NAME = N'Booking', 
		-- 	--FILENAME = N'/var/opt/mssql/data/Booking.mdf' , 
		-- 	SIZE = 73728KB , 
		-- 	MAXSIZE = UNLIMITED, 
		-- 	FILEGROWTH = 65536KB 
		-- )
		-- LOG ON 
		-- ( 
		-- 	NAME = N'Booking_log', 
		-- 	--FILENAME = N'/var/opt/mssql/data/Booking_log.ldf' , 
		-- 	SIZE = 73728KB , 
		-- 	MAXSIZE = 2048GB , 
		-- 	FILEGROWTH = 65536KB 
		-- )

GO

PRINT 'Create database - End'

GO

USE [Booking]

GO

PRINT 'Create tables - Start'

GO

CREATE TABLE [dbo].[city]
(
	[city_id] [int] IDENTITY(1,1) NOT NULL,
	[city_name] [varchar](255) NULL,
	[country] [varchar](255) NULL,
	PRIMARY KEY CLUSTERED 
	(
		[city_id] ASC
	)
)

GO

CREATE TABLE [dbo].[destination]
(
	[destination_id] [int] IDENTITY(1,1) NOT NULL,
	[city_id] [int] NULL,
	[destination_name] [nvarchar](255) NULL,
	[coordinates_long] [decimal](19, 4) NULL,
	[coordinates_lat] [decimal](19, 4) NULL,
	PRIMARY KEY CLUSTERED 
	(
		[destination_id] ASC
	)
) 

GO

CREATE TABLE [dbo].[calculate_distance]
(
	[calculate_distance_id] [int] IDENTITY(1,1) NOT NULL,
	[destination_id] [int] NULL,
	[calculate_distance_starttime] [datetime] NULL,
	[calculate_distance_endtime] [datetime] NULL,
	[inserted_at] [datetime] NOT NULL,
	PRIMARY KEY CLUSTERED 
	(
		[calculate_distance_id] ASC
	)
) 

GO

CREATE TABLE [dbo].[distance_result]
(
	[distance_result_id] [int] IDENTITY(1,1) NOT NULL,
	[booking_property_id] [int] NULL,
	[destination_id] [int] NULL,
	[city_id] [int] NULL,
	[walking_response_status] [nchar](255) NULL,
	[walking_duration_seconds] [bigint] NULL,
	[walking_distance_meters] [bigint] NULL,
	[driving_response_status] [nchar](255) NULL,
	[driving_duration_seconds] [bigint] NULL,
	[driving_distance_meters] [bigint] NULL,
	[transit_reponse_status] [nchar](255) NULL,
	[transit_duration_seconds] [bigint] NULL,
	[transit_distance_meters] [bigint] NULL,
	PRIMARY KEY CLUSTERED 
	(
		[distance_result_id] ASC
	)
) 

GO

CREATE TABLE [dbo].[search]
(
	[search_id] [int] IDENTITY(1,1) NOT NULL,
	[city_id] [int] NULL,
	[search_starttime] [datetime] NULL,
	[search_endtime] [datetime] NULL,
	[search_date] [date] NULL,
	[no_days_before_travel] [int] NULL,
	[currency] [nvarchar](3) NULL,
	[language] [nvarchar](10) NULL,
	[check_in_date] [date] NULL,
	[check_out_date] [date] NULL,
	[no_nights] [int] NULL,
	[no_adults] [int] NULL,
	[no_childrens] [int] NULL,
	[no_rooms] [int] NULL,
	[is_business_trip] [bit] NULL,
	[get_only_avaliable] [bit] NULL,
	[inserted_at] [datetime] NOT NULL,
	PRIMARY KEY CLUSTERED 
	(
		[search_id] ASC
	)
) 

GO

CREATE TABLE [dbo].[search_result]
(
	[property_id] [int] IDENTITY(1,1) NOT NULL,
	[search_id] [int] NULL,
	[city_id] [int] NULL,
	[page_no] [int] NULL,
	[booking_property_id] [int] NULL,
	[property_name] [nvarchar](500) NULL,
	[property_offer_url] [nvarchar](2500) NULL,
	[property_url] [nvarchar](2500) NULL,
	[property_type_badge] [nvarchar](500) NULL,
	[booking_rating_star] [int] NULL,
	[hotel_own_rating] [int] NULL,
	[hotel_rating_star] [int] NULL,
	[booking_partner] [bit] NULL,
	[coordinates_long] [decimal](19, 4) NULL,
	[coordinates_lat] [decimal](19, 4) NULL,
	[location_name] [nvarchar](500) NULL,
	[no_reviews] [int] NULL,
	[review_score] [decimal](19, 4) NULL,
	[original_price] [decimal](19, 4) NULL,
	[promo_price] [decimal](19, 4) NULL,
	[proposed_room_type] [nvarchar](500) NULL,
	[is_avaliable] [bit] NULL,
	[inserted_at] [datetime] NOT NULL,
	PRIMARY KEY CLUSTERED 
	(
		[property_id] ASC
	)
) 

GO

ALTER TABLE [dbo].[search] 
	ADD CONSTRAINT [DF_search_inserted_at]  
	DEFAULT (getdate()) 
	FOR [inserted_at]

GO

ALTER TABLE [dbo].[calculate_distance] 
	ADD CONSTRAINT [DF_calculate_distance_inserted_at]  
	DEFAULT (getdate()) 
	FOR [inserted_at]

GO

ALTER TABLE [dbo].[search_result] 
	ADD CONSTRAINT [DF_offer_list_inserted_at]  
	DEFAULT (getdate()) 
	FOR [inserted_at]

GO


PRINT 'Create tables - End'


exec sp_configure 'show advanced options',1
reconfigure
    
    
exec sp_configure 'Agent XPs',1
reconfigure