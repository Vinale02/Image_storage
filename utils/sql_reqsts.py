add_image = """
    INSERT INTO images (
        filename, 
        original_name, 
        size, 
        upload_time, 
        file_type 
        ) 
    VALUES (
        %s, 
        %s, 
        %s, 
        %s, 
        %s
    );
"""

get_images_data = """
    SELECT 
        id,
        filename,
        original_name,
        size,
        upload_time,
        file_type 
    FROM images
    ORDER BY upload_time DESC;
    """

delete_image_data = """
    DELETE FROM images
    WHERE id = %s;
    """

get_image_name_for_delete = """
    SELECT filename
    FROM images
    WHERE id = %s;
    """